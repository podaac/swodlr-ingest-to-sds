'''Lambda to bootstrap step function execution'''
import json
import boto3
from podaac.swodlr_ingest_to_sds.utilities import utils

stepfunctions = boto3.client('stepfunctions')
ingest_sf_arn = utils.get_param('stepfunction_arn')
logger = utils.get_logger(__name__)


def lambda_handler(event, _context):
    '''Starts step function execution'''

    sf_input = json.dumps(event, separators=(',', ':'))
    result = stepfunctions.start_execution(
        stateMachineArn=ingest_sf_arn,
        input=sf_input
    )
    logger.info('Started step function execution: %s', result['executionArn'])
