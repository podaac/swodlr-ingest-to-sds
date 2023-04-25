'''Command line tool for submitting an individual granule to the SDS'''
import logging
from argparse import ArgumentParser
import json
from pathlib import PurePath
from urllib.parse import urlsplit
import boto3

logging.basicConfig(level=logging.INFO)
sns = boto3.client('sns')


def main():
    '''
    Main entry point for the script
    '''

    parser = ArgumentParser()

    parser.add_argument('topic_arn')
    parser.add_argument('s3_url')

    args = parser.parse_args()

    res = sns.publish(
        TopicArn=args.topic_arn,
        Message=json.dumps(_gen_cnm_r(args.s3_url))
    )
    logging.info('Sent SNS message; id: %s', res['MessageId'])


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
