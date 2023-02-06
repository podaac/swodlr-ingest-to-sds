import json
import boto3
import logging
from podaac.swodlr_ingest_to_sds.utils import get_param

stepfunctions = boto3.client('stepfunctions')
ingest_sf_arn = get_param('stepfunction_arn')


def lambda_handler(event, context):
    input = json.dumps(event, separators=(',', ':'))
    result = stepfunctions.start_execution(arn=ingest_sf_arn, input=input)
    logging.info('Started step function execution: %s', result['executionArn'])
