'''Tests for the bootstrap module'''
import os
from unittest import TestCase
from unittest.mock import patch

TEST_ARN = 'ABC123'

with (
    patch('boto3.client'),
    patch.dict(os.environ, {
        'SWODLR_ENV': 'dev',
        'SWODLR_stepfunction_arn': TEST_ARN
    })
):
    from podaac.swodlr_ingest_to_sds import bootstrap


class TestBootstrap(TestCase):
    '''Tests for the bootstrap module'''

    def test_bootstrap(self):
        '''
        Test the lambda handler of the bootstrap module by submitting an event
        and checking output for the transformed event
        '''
        event = {
            'a': 42,
            'b': True,
            'c': 'ipsum lorem'
        }

        with (
            patch.object(
                bootstrap.stepfunctions,
                'start_execution'
            ) as mock_exec
        ):
            bootstrap.lambda_handler(event, None)
            mock_exec.assert_called_once_with(
                arn=TEST_ARN,
                input='{"a":42,"b":true,"c":"ipsum lorem"}'
            )
