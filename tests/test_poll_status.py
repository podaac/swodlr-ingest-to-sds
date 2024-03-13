'''Tests for the poll_status module'''
from unittest import TestCase
from unittest.mock import patch
from pathlib import Path
import json
from os import environ
from podaac.swodlr_ingest_to_sds.utilities import utils

with (
    patch.dict(environ, {
        'SWODLR_ENV': 'dev',
        'SWODLR_sds_username': 'AAAAAA',
        'SWODLR_sds_password': 'BBBBBB'
    })
):
    from podaac.swodlr_ingest_to_sds import poll_status


class TestPollStatus(TestCase):
    '''Tests for the poll_status module'''
    data_path = Path(__file__).parent.joinpath('data')
    poll_event_path = data_path.joinpath('poll_event.json')
    with open(poll_event_path, encoding='utf-8') as f:
        poll_event = json.load(f)

    @patch('boto3.resource')
    def test_poll_status(self, _):
        '''
        Test the lambda handler for the poll_status module by submitting two
        jobs, polling their status, verifying that the correct jobs are
        updated in the database, and verifying that remaining jobs are
        returned in the event.
        '''
        _statuses = [
            {'status': 'job-completed'},
            {'status': 'job-started'}
        ]

        def _mock_get_info():
            nonlocal _statuses
            return _statuses.pop()

        event = None
        with (
            patch('otello.mozart.Mozart.get_job_by_id') as mock_get_job_by_id,
        ):
            mock_get_job_by_id().get_info.side_effect = _mock_get_info
            event = poll_status.lambda_handler(self.poll_event, None)

        self.assertEqual(len(event['jobs']), 1)
        self.assertDictEqual(event['jobs'][0], {
            'job_id': 'job_id_1',
            'granule_id': 'granule_id_1'
        })

        valid_statuses = {
            'granule_id_1': 'job-started',
            'granule_id_2': 'job-completed'
        }

        # pylint: disable=no-member
        update_item_calls = utils.ingest_table.update_item.call_args_list
        self.assertEqual(len(update_item_calls), 2)
        for call in update_item_calls:
            kwargs = call.kwargs
            key = kwargs['Key']['granule_id']
            status = kwargs['ExpressionAttributeValues'][':status']

            self.assertEqual(status, valid_statuses[key])
            del valid_statuses[key]
