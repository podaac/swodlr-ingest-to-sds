from unittest import TestCase
from unittest.mock import patch
from podaac.swodlr_ingest_to_sds import utils
from pathlib import Path
import json
from os import environ

with (
  patch('boto3.client'),
  patch('boto3.resource'),
  patch('otello.mozart.Mozart.get_job_type'),
  patch.dict(environ, {
    'SWODLR_ENV': 'dev',
    'SWODLR_sds_username': 'AAAAAA',
    'SWODLR_sds_password': 'BBBBBB',
    'SWODLR_ingest_table_name': 'CCCCCC'
  })
):
  from podaac.swodlr_ingest_to_sds import submit_to_sds, utils

class TestSubmitToSds(TestCase):
  data_path = Path(__file__).parent.joinpath('data')
  valid_event_path = data_path.joinpath('valid_event.json')
  with open(valid_event_path) as f:
    valid_event = json.load(f)

  invalid_event_path = data_path.joinpath('invalid_event.json')
  with open(invalid_event_path) as f:
    invalid_event = json.load(f)

  def test_valid_submit(self):
    submit_to_sds.lambda_handler(self.valid_event, None)

    input_calls = submit_to_sds.ingest_job_type.set_input_params.call_args_list
    submit_calls = submit_to_sds.ingest_job_type.submit_job.call_args_list
    put_item_calls = utils.ingest_table.batch_writer().__enter__().put_item.call_args_list

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
    for call in input_calls:
      # ensure no duplicates
      _valid_filenames = valid_filenames.copy()
      _valid_urls = valid_urls.copy()

      params = call.args[0]
      self.assertIn(params['id'], _valid_filenames)
      self.assertIn(params['data_file'], _valid_filenames)
      self.assertIn(params['data_url'], _valid_urls)

      _valid_filenames.remove(params['data_file'])
      _valid_urls.remove(params['data_url'])

    # put_item calls
    for call in put_item_calls:
      _valid_granule_ids = valid_granule_ids.copy()
      _valid_urls = valid_urls.copy()

      self.assertIn(call.kwargs['Item']['granule_id']['S'], _valid_granule_ids)
      self.assertIn(call.kwargs['Item']['s3_url']['S'], _valid_urls)
  
      _valid_granule_ids.remove(call.kwargs['Item']['granule_id']['S'])
      _valid_urls.remove(call.kwargs['Item']['s3_url']['S'])

    # submit_job calls
    for call in submit_calls:
      self.assertIn(call.kwargs['tag'], valid_tags)
      valid_tags.remove(call.kwargs['tag'])

    # batch_get_item calls
    submit_to_sds.dynamodb.batch_get_item.assert_called_once_with(
      RequestItems={
        'CCCCCC': {
          'Keys': [
            {'granule_id': {'S': 'test-1'}},
            {'granule_id': {'S': 'test-2'}},
            {'granule_id': {'S': 'test-3'}},
          ]
        }
      },
      ProjectionExpression='granule_id',
      ReturnConsumedCapacity='NONE'
    )

    submit_to_sds.ingest_job_type.set_input_params.reset_mock()
    submit_to_sds.ingest_job_type.submit_job.reset_mock()

  def test_invalid_submit(self):
    with self.assertRaises(RuntimeError):
      submit_to_sds.lambda_handler(self.invalid_event, None)
  