'''Lambda to submit granules to the SDS for ingestion'''
from datetime import datetime
import json
import logging
from pathlib import PurePath
from urllib.parse import urlsplit, urlunsplit
import boto3
from podaac.swodlr_ingest_to_sds.errors import DataNotFoundError
from podaac.swodlr_ingest_to_sds.utils import (
    mozart_client, get_param, ingest_table
)

ACCEPTED_EXTS = ['nc']
INGEST_QUEUE_URL = get_param('ingest_queue_url')
INGEST_TABLE_NAME = get_param('ingest_table_name')
PCM_RELEASE_TAG = get_param('sds_pcm_release_tag')

dynamodb = boto3.client('dynamodb')
sqs = boto3.client('sqs')

ingest_job_type = mozart_client.get_job_type(
    f'job-INGEST_STAGED:{PCM_RELEASE_TAG}'
)

ingest_job_type.initialize()


def lambda_handler(event, _context):
    '''
    Lambda handler which submits granules to the SDS for ingestion if they are
    not already ingested and inserts the granule and job info into DynamoDB
    '''

    logging.debug('Records received: %d', len(event['Records']))

    granules = {}
    for record in event['Records']:
        try:
            granule = _parse_record(record)
            granules[granule['id']] = granule
        except (DataNotFoundError, json.JSONDecodeError):
            logging.exception('Failed to parse record')

    lookup_results = dynamodb.batch_get_item(
        RequestItems={
            INGEST_TABLE_NAME: {
                'Keys': [{'granule_id': {'S': granule['id']}}
                         for granule in granules.values()]
            }
        },
        ProjectionExpression='granule_id',
        ReturnConsumedCapacity='NONE'
    )

    for item in lookup_results['Responses'][INGEST_TABLE_NAME]:
        granule_id = item['granule_id']['S']
        if granule_id in granules:
            logging.info('Granule already ingested: %s', granule_id)
            del granules[granule_id]

    jobs = []
    with ingest_table.batch_writer() as batch:
        for granule in granules.values():
            try:
                job = _ingest_granule(granule)
                jobs.append({'granule_id': granule['id'], 'job_id': job['job_id']})

                batch.put_item(
                    Item={
                        'granule_id': {'S': granule['id']},
                        's3_url': {'S': granule['s3_url']},
                        'job_id': {'S': job['job_id']},
                        'status': {'S': job['status']},
                        'last_check': {'S': job['timestamp']}
                    }
                )
            except Exception:
                logging.exception('Failed to ingest granule')

    return {'jobs': jobs}


def _parse_record(record):
    cmr_r_message = json.loads(record['body'])
    identifier = cmr_r_message['identifier']
    filename, s3_url = _extract_s3_url(cmr_r_message)

    return {
        'id': identifier,
        'filename': filename,
        's3_url': s3_url,
        'messageId': record['messageId'],
        'receiptHandle': record['receiptHandle']
    }


def _ingest_granule(granule):
    filename = granule['filename']
    s3_url = granule['s3_url']

    logging.debug('Ingesting granule id: %s', granule['id'])

    job_params = _gen_mozart_job_params(filename, s3_url)
    tag = f'ingest_file_otello__{filename}'

    ingest_job_type.set_input_params(job_params)
    job = ingest_job_type.submit_job(tag=tag)
    timestamp = datetime.now().isoformat()
    logging.info('Submitted to sds: %s', granule['id'])

    return {
        'job_id': job.job_id,
        'status': 'job-queued',
        'timestamp': timestamp
    }


def _extract_s3_url(cnm_r_message):
    files = cnm_r_message['product']['files']
    for file in files:
        ext = PurePath(file['name']).suffix[1:].lower()
        if ext in ACCEPTED_EXTS:
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
            logging.debug("S3 url: %s", s3_elements)

            return (file['name'], s3_url)

        logging.debug('Rejected file: %s', file['name'])

    raise DataNotFoundError()


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
        'create_hash': 'true',  # Why is this a string?
        'hash_type': 'md5',
        'update_s3_tag': False
    }

    return params
