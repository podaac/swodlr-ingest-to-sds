import boto3
from dotenv import load_dotenv
import sys
from os import getenv
from otello.mozart import Mozart
from requests import Session

load_dotenv()


class Utils:
    APP_NAME = 'swodlr'
    SSM_PATH = f'/service/{APP_NAME}/ingest/'

    def __init__(self):
        self.env = getenv('SWODLR_ENV', 'prod')

        if self.env == 'prod':
            self._load_params_from_ssm()

    def _load_params_from_ssm(self):
        ssm = boto3.client('ssm')
        parameters = ssm.get_parameters_by_path(
            path=Utils.SSM_PATH,
            with_decryption=True
        )['Parameters']

        self._ssm_parameters = {}

        for param in parameters:
            self._ssm_parameters[param['Name']] = param['Value']

    def get_param(self, name):
        if (self.env == 'prod'):
            return self._ssm_parameters.get(name)
        else:
            return getenv(f'{self.APP_NAME.upper()}_{name}')

    @property
    def mozart_client(self):
        if not hasattr(self, '_mozart_client'):
            cfg = {
                'host': self.get_param('sds_host'),
                'auth': True,
                'username': self.get_param('sds_username'),
                'password': self.get_param('sds_password')
            }
            client = Mozart(cfg)

            self._mozart_client = client

        return self._mozart_client

    @property
    def ingest_table(self):
        if not hasattr(self, '_ingest_table'):
            dynamodb = boto3.resource('dynamodb')
            self._ingest_table = dynamodb.Table(
                self.get_param('ingest_table_name'))

        return self._ingest_table


sys.modules[__name__] = Utils()
