from unittest import TestCase
from unittest.mock import patch, MagicMock
from podaac.swodlr_ingest_to_sds import utils
from otello.mozart import Mozart
from pathlib import Path
import json
from os import environ

with (
    patch('boto3.client'),
    patch('boto3.resource'),
    patch.dict(environ, {
        'SWODLR_ENV': 'dev',
        'SWODLR_sds_username': 'AAAAAA',
        'SWODLR_sds_password': 'BBBBBB'
    })
):
    from podaac.swodlr_ingest_to_sds import poll_status

class TestPollStatus(TestCase):
    data_path = Path(__file__).parent.joinpath('data')
    poll_event_path = data_path.joinpath('poll_event.json')
    with open(poll_event_path) as f:
        poll_event = json.load(f)

    def test_poll_status(self):
        _statuses = ['job-completed', 'job-started']
        def _mock_get_status():
            nonlocal _statuses
            return _statuses.pop()

        event = None
        with (
            patch('otello.mozart.Mozart.get_job_by_id') as mock_get_job_by_id,
        ):
            mock_get_job_by_id().get_status.side_effect = _mock_get_status
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

        update_item_calls = utils.ingest_table.update_item.call_args_list
        self.assertEqual(len(update_item_calls), 2)
        for call in update_item_calls:
            kwargs = call.kwargs
            key = kwargs['Key']['granule_id']['S']
            status = kwargs['ExpressionAttributeValues'][':status']['S']

            self.assertEqual(status, valid_statuses[key])
            del valid_statuses[key]
