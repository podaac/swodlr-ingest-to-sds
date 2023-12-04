'''Shared utilities for ingest-to-sds lambdas'''
import boto3
from otello.mozart import Mozart

from podaac.swodlr_common.utilities import BaseUtilities


class Utilities(BaseUtilities):
    '''Utility functions implemented as a singleton'''
    APP_NAME = 'swodlr'
    SERVICE_NAME = 'ingest-to-sds'

    def __init__(self):
        super().__init__(Utilities.APP_NAME, Utilities.SERVICE_NAME)

    @property
    def mozart_client(self):
        '''
        Lazily creates a Mozart client
        '''
        if not hasattr(self, '_mozart_client'):
            host = self.get_param('sds_host')
            username = self.get_param('sds_username')
            cfg = {
                'host': host,
                'auth': True,
                'username': username
            }

            # pylint: disable=attribute-defined-outside-init
            self._mozart_client = Mozart(cfg, session=self._get_sds_session())

        return self._mozart_client

    @property
    def ingest_table(self):
        '''
        Lazily creates a DynamoDB table resource
        '''
        if not hasattr(self, '_ingest_table'):
            dynamodb = boto3.resource('dynamodb')
            # pylint: disable=attribute-defined-outside-init
            self._ingest_table = dynamodb.Table(
                self.get_param('ingest_table_name')
            )

        return self._ingest_table

    @property
    def available_tiles_table(self):
        '''
        Lazily creates a DynamoDB table resource
        '''
        if not hasattr(self, '_available_tiles_table'):
            dynamodb = boto3.resource('dynamodb')
            # pylint: disable=attribute-defined-outside-init
            self._available_tiles_table = dynamodb.Table(
                self.get_param('available_tiles_table_name')
            )

        return self._available_tiles_table


utils = Utilities()
