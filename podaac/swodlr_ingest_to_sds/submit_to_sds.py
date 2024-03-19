'''Lambda to submit granules to the SDS for ingestion'''
from datetime import datetime
import json
from pathlib import PurePath
from urllib.parse import urlsplit, urlunsplit
import boto3
from podaac.swodlr_common import sds_statuses
from podaac.swodlr_ingest_to_sds.errors import DataNotFoundError
from podaac.swodlr_ingest_to_sds.utilities import utils

ACCEPTED_EXTS = ['nc']
INGEST_QUEUE_URL = utils.get_param('ingest_queue_url')
INGEST_TABLE_NAME = utils.get_param('ingest_table_name')
PCM_RELEASE_TAG = utils.get_param('sds_pcm_release_tag')

dynamodb = boto3.client('dynamodb')
sqs = boto3.client('sqs')

logger = utils.get_logger(__name__)
ingest_job_type = utils.mozart_client.get_job_type(
    f'job-INGEST_STAGED:{PCM_RELEASE_TAG}'
)
ingest_job_type.initialize()


def lambda_handler(event, _context):
    '''
    Lambda handler which submits granules to the SDS for ingestion if they are
    not already ingested and inserts the granule and job info into DynamoDB
    '''

    logger.debug('Records received: %d', len(event['Records']))

    granules = {}
    for record in event['Records']:
        try:
            granule = _parse_record(record)
            granules[granule['id']] = granule
        except (DataNotFoundError, json.JSONDecodeError):
            logger.exception('Failed to parse record')

    lookup_results = dynamodb.batch_get_item(
        RequestItems={
            INGEST_TABLE_NAME: {
                'Keys': [{'granule_id': {'S': granule['id']}}
                         for granule in granules.values()],
                'ProjectionExpression': 'granule_id, #status',
                'ExpressionAttributeNames': {'#status': 'status'}
            }
        },
        ReturnConsumedCapacity='NONE'
    )

    for item in lookup_results['Responses'][INGEST_TABLE_NAME]:
        granule_id = item['granule_id']['S']
        status = item['status']['S']
        if granule_id in granules and status in sds_statuses.SUCCESS:
            logger.info('Granule already ingested: %s', granule_id)
            del granules[granule_id]

    jobs = []
    with utils.ingest_table.batch_writer() as batch:
        for granule in granules.values():
            try:
                job = _ingest_granule(granule)
                jobs.append({
                    'granule_id': granule['id'],
                    'job_id': job['job_id']
                })

                batch.put_item(
                    Item={
                        'granule_id': granule['id'],
                        's3_url': granule['s3_url'],
                        'job_id':  job['job_id'],
                        'status': job['status'],
                        'last_check': job['timestamp']
                    }
                )
            # Otello throws generic Exceptions
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception(
                    'Failed to ingest granule id: %s', granule['id']
                )

    return {'jobs': jobs}


def _parse_record(record):
    cmr_r_message = json.loads(record['body'])
    filename, s3_url = _extract_s3_url(cmr_r_message)
    identifier = filename.split('.', 1)[0]

    return {
        'id': identifier,
        'filename': filename,
        's3_url': s3_url
    }


def _ingest_granule(granule):
    filename = granule['filename']
    s3_url = granule['s3_url']

    logger.debug('Ingesting granule id: %s', granule['id'])

    job_params = _gen_mozart_job_params(filename, s3_url)
    tag = f'ingest_file_otello__{filename}'

    ingest_job_type.set_input_params(job_params)
    job = ingest_job_type.submit_job(tag=tag)
    timestamp = datetime.now().isoformat()
    logger.info(
        'Submitted to sds - granule id: %s, job id: %s',
        granule['id'], job.job_id
    )

    return {
        'job_id': job.job_id,
        'status': 'job-queued',
        'timestamp': timestamp
    }


def _extract_s3_url(cnm_r_message, strict=True):
    files = cnm_r_message['product']['files']
    for file in files:
        if _accept_file(file, strict):
            url_elements = urlsplit(file['uri'])
            if url_elements.scheme == 's3':
                # Accept s3 urls as-is
                return (file['name'], file['uri'])

            path_segments = url_elements.path[1:].split('/')
            s3_elements = (
                's3',                         # scheme
                path_segments[0],             # netloc
                '/'.join(path_segments[1:]),  # path
                '',                           # query
                ''                            # fragment
            )

            s3_url = urlunsplit(s3_elements)
            logger.debug("S3 url: %s", s3_elements)

            return (file['name'], s3_url)

        logger.debug('Rejected file: %s', file['name'])

    if strict:
        # Rerun without strict mode
        return _extract_s3_url(cnm_r_message, False)

    raise DataNotFoundError()


def _accept_file(file, strict):
    if strict:
        ext = PurePath(file['name']).suffix[1:].lower()
        return ext in ACCEPTED_EXTS

    return file['type'] == 'data'


def _gen_mozart_job_params(filename, url):
    params = {
        'id': filename,
        'data_url': url,
        'data_file': filename,
        'prod_met': {
            'tags': ['ISL', url],
            'met_required': False,
            'restaged': False,
            'ISL_urls': url
        },
        'create_hash': 'false',   # Why is this a string?
        'update_s3_tag': 'false'  # Why is this a string?
    }

    return params
