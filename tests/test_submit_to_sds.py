'''Tests for the submit_to_sds module'''
from unittest import TestCase
from unittest.mock import patch
from pathlib import Path
import json
from os import environ


with (
    patch('boto3.client'),
    patch('boto3.resource'),
    patch('otello.mozart.Mozart.get_job_type'),
    patch.dict(environ, {
        'SWODLR_ENV': 'dev',
        'SWODLR_sds_username': 'test_username',
        'SWODLR_sds_password': 'test_password',
        'SWODLR_ingest_table_name': 'test_ingest_table_name',
        'SWODLR_ingest_queue_url': 'test_ingest_queue_url'
    })
):
    from podaac.swodlr_ingest_to_sds import submit_to_sds, utils


class TestSubmitToSds(TestCase):
    '''Tests for the submit_to_sds module'''
    data_path = Path(__file__).parent.joinpath('data')
    valid_event_path = data_path.joinpath('valid_sqs_event.json')
    with open(valid_event_path, encoding='utf-8') as f:
        valid_event = json.load(f)

    invalid_event_path = data_path.joinpath('invalid_sqs_event.json')
    with open(invalid_event_path, encoding='utf-8') as f:
        invalid_event = json.load(f)

    def test_valid_submit(self):
        '''
        Test the lambda handler for the submit_to_sds module by submitting
        three jobs, verifying all jobs are submitted, and verifying that
        the correct items are added to the ingest table.
        '''

        submit_to_sds.lambda_handler(self.valid_event, None)

        submit_calls = submit_to_sds.ingest_job_type.submit_job.call_args_list
        input_calls = submit_to_sds.ingest_job_type.set_input_params\
            .call_args_list
        # pylint: disable=no-member,unnecessary-dunder-call
        put_item_calls = utils.ingest_table.batch_writer().__enter__()\
            .put_item.call_args_list

        self.assertEqual(len(input_calls), 3)
        self.assertEqual(len(submit_calls), 3)
        self.assertEqual(len(put_item_calls), 3)

        valid_granule_ids = {'test-1', 'test-2', 'test-3'}
        valid_filenames = {'test-1.nc', 'test-2.nc', 'test-3.nc'}
        valid_urls = {
            's3://bucket/test/test-1.nc',
            's3://bucket/test/test-2.nc',
            's3://bucket/test/test-3.nc'
        }
        valid_tags = {
            'ingest_file_otello__test-1.nc',
            'ingest_file_otello__test-2.nc',
            'ingest_file_otello__test-3.nc'
        }

        # set_input_params calls
        _valid_filenames = valid_filenames.copy()
        _valid_urls = valid_urls.copy()
        for call in input_calls:
            params = call.args[0]
            self.assertIn(params['id'], _valid_filenames)
            self.assertIn(params['data_file'], _valid_filenames)
            self.assertIn(params['data_url'], _valid_urls)

            _valid_filenames.remove(params['data_file'])
            _valid_urls.remove(params['data_url'])

        # put_item calls
        _valid_granule_ids = valid_granule_ids.copy()
        _valid_urls = valid_urls.copy()
        for call in put_item_calls:
            self.assertIn(call.kwargs['Item']
                          ['granule_id'], _valid_granule_ids)
            self.assertIn(call.kwargs['Item']['s3_url'], _valid_urls)

            _valid_granule_ids.remove(call.kwargs['Item']['granule_id'])
            _valid_urls.remove(call.kwargs['Item']['s3_url'])

        # submit_job calls
        _valid_tags = valid_tags.copy()
        for call in submit_calls:
            self.assertIn(call.kwargs['tag'], _valid_tags)
            _valid_tags.remove(call.kwargs['tag'])

        # batch_get_item call
        submit_to_sds.dynamodb.batch_get_item.assert_called_once_with(
            RequestItems={
                'test_ingest_table_name': {
                    'Keys': [
                        {'granule_id': {'S': 'test-1'}},
                        {'granule_id': {'S': 'test-2'}},
                        {'granule_id': {'S': 'test-3'}},
                    ],
                    'ProjectionExpression': 'granule_id'
                }
            },
            ReturnConsumedCapacity='NONE'
        )

    def test_invalid_submit(self):
        '''
        Test the lambda handler for the submit_to_sds module by submitting
        an invalid event, verifying that a RuntimeException is raised.
        '''
        event = submit_to_sds.lambda_handler(self.invalid_event, None)
        self.assertEqual(len(event['jobs']), 0)

    def tearDown(self):
        '''
        Reset mocks after each test run
        '''

        submit_to_sds.ingest_job_type.set_input_params.reset_mock()
        submit_to_sds.ingest_job_type.submit_job.reset_mock()
        # pylint: disable=unnecessary-dunder-call
        utils.ingest_table.batch_writer().__enter__().put_item.reset_mock()
        submit_to_sds.dynamodb.batch_get_item.reset_mock()
