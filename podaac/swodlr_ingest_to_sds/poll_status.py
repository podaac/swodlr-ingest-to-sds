'''Lambda to poll SDS for job status and update DynamoDB'''
from datetime import datetime
from copy import deepcopy
import logging
# pylint: disable=no-name-in-module
from podaac.swodlr_ingest_to_sds.utils import mozart_client, ingest_table

SUCCESS_STATUSES = {'job-completed'}
FAIL_STATUSES = {'job-failed', 'job-offline', 'job-deduped'}


def lambda_handler(event, _context):
    '''
    Polls SDS for job status and updates DynamoDB. Returns the remaining jobs
    that have not completed.
    '''
    new_event = deepcopy(event)

    for item in event['jobs']:
        granule_id = item['granule_id']
        job_id = item['job_id']

        job = mozart_client.get_job_by_id(job_id)

        try:
            status = job.get_status()
            timestamp = datetime.now().isoformat()
            logging.debug('granule id: %s; job id: %s; status: %s',
                          granule_id, job_id, status)

            ingest_table.update_item(
                Key={'granule_id': {'S': granule_id}},
                UpdateExpression=(
                    'SET status = :status,'
                    'last_check = :last_check'
                ),
                ExpressionAttributeValues={
                    ':status': {'S': status},
                    ':last_check': {'S': timestamp}
                }
            )

            if status in FAIL_STATUSES:
                logging.error('Job id: %s; status: %s', job_id, status)
                new_event['jobs'].remove(item)
            elif status in SUCCESS_STATUSES:
                logging.info('Job id: %s; status: %s', job_id, status)
                new_event['jobs'].remove(item)
        # Otello raises very generic exceptions
        except Exception:  # pylint: disable=broad-except
            logging.exception(
                'Failed to get status: %s',
                job_id
            )

    return new_event
