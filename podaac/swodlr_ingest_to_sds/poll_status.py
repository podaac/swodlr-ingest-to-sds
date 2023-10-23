'''Lambda to poll SDS for job status and update DynamoDB'''
from datetime import datetime
from copy import deepcopy
import logging
import re
from podaac.swodlr_ingest_to_sds.utils import (
    mozart_client, ingest_table, available_tiles_table
)


SUCCESS_STATUSES = {'job-completed'}
FAIL_STATUSES = {'job-failed', 'job-offline', 'job-deduped'}
PRODUCT_REGEX = re.compile(
    r'_(?P<product>PIXC(Vec)?)_(?P<cycle>\d{3})_(?P<pass>\d{3})_(?P<tile>\d{3})(?P<direction>(R|L))_'  # pylint: disable=line-too-long # noqa: E501
)


def lambda_handler(event, _context):
    '''
    Polls SDS for job status and updates DynamoDB. Returns the remaining jobs
    that have not completed.
    '''
    new_event = deepcopy(event)

    for item in event['jobs']:
        granule_id = item['granule_id']
        job_id = item['job_id']

        try:
            job = mozart_client.get_job_by_id(job_id)
            info = job.get_info()
            status = info['status']
            timestamp = datetime.now().isoformat()
            logging.debug('granule id: %s; job id: %s; status: %s',
                          granule_id, job_id, status)

            update_expression = (
                'SET #status = :status'
                ',#last_check = :last_check'
            )
            expression_attribute_names = {
                '#status': 'status',
                '#last_check': 'last_check'
            }
            expression_attribute_values = {
                ':status': status,
                ':last_check': timestamp
            }

            if 'traceback' in info:
                update_expression += ',#traceback = :traceback'
                expression_attribute_names['#traceback'] = 'traceback'
                expression_attribute_values[':traceback'] = info['traceback']

            ingest_table.update_item(
                Key={'granule_id': granule_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )

            if status in FAIL_STATUSES:
                logging.error('Job id: %s; status: %s', job_id, status)
                if 'traceback' in info:
                    logging.error(
                        'Job id: %s; traceback: %s', job_id, info['traceback']
                    )

                new_event['jobs'].remove(item)
            elif status in SUCCESS_STATUSES:
                logging.info('Job id: %s; status: %s', job_id, status)

                # Insert into available tiles table
                cpt = _extract_cpt(granule_id)
                if cpt is not None:
                    tile_id = f'{cpt["product"]},{cpt["cycle"]},{cpt["pass"]},{cpt["tile"]}'  # pylint: disable=line-too-long # noqa: E501
                    available_tiles_table.put_item(
                        Item={'tile_id': {'S': tile_id}}
                    )

                new_event['jobs'].remove(item)  # Remove from queue
        # Otello raises very generic exceptions
        except Exception:  # pylint: disable=broad-except
            logging.exception('Failed to get status: %s', job_id)

    return new_event


def _extract_cpt(granule_id):
    parsed_id = PRODUCT_REGEX.match(granule_id)
    if parsed_id is None:
        return None

    return {
        'product': parsed_id.group('product'),
        'cycle': int(parsed_id.group('cycle')),
        'pass': int(parsed_id.group('pass')),
        'tile': int(parsed_id.group('tile')) + parsed_id.group('direction')
    }
