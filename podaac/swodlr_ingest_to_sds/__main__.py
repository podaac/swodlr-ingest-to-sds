'''Command line tool for submitting an individual granule to the SDS'''

from argparse import ArgumentParser
import json
import logging
from pathlib import PurePath
from time import sleep
from unittest.mock import patch
from urllib.parse import urlsplit


# Patch out AWS clients and resources
with patch('boto3.client'), patch('boto3.resource'):
    from podaac.swodlr_ingest_to_sds import submit_to_sds, poll_status


def main():
    '''
    Main entry point for the script
    '''

    parser = ArgumentParser()
    parser.add_argument('s3_url', help='S3 URL of granule to ingest')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    s3_url = args.s3_url

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    event = _gen_event(s3_url)
    event = submit_to_sds.lambda_handler(event, None)
    while len(event['jobs']) > 0:
        logging.info('Sleeping for 20 seconds')
        sleep(20)
        event = poll_status.lambda_handler(event, None)


def _gen_event(s3_url):
    event = {
        'Records': [{
            'body': json.dumps(_gen_cnm_r(s3_url)),
            'messageId': '',
            'receiptHandle': ''
        }]
    }
    return event


def _gen_cnm_r(s3_url):
    url_components = urlsplit(s3_url)
    path = PurePath(url_components.path)

    filename = path.name
    granule_id = path.stem

    cmr_r = {
        'identifier': granule_id,
        'product': {
            'files': [{
                'name': filename,
                'uri': s3_url
            }]
        }
    }

    return cmr_r


if __name__ == '__main__':
    main()
