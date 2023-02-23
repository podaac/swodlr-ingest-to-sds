'''Lambda to bootstrap step function execution'''
import json
import logging
import boto3
# pylint: disable=no-name-in-module
from podaac.swodlr_ingest_to_sds.utils import get_param

stepfunctions = boto3.client('stepfunctions')
ingest_sf_arn = get_param('stepfunction_arn')


def lambda_handler(event, _context):
    '''Starts step function execution'''

    sf_input = json.dumps(event, separators=(',', ':'))
    result = stepfunctions.start_execution(arn=ingest_sf_arn, input=sf_input)
    logging.info('Started step function execution: %s', result['executionArn'])
