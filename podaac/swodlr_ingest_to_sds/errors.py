'''swodlr-ingest-to-sds specific errors'''


class DataNotFoundError(RuntimeError):
    '''
    Thrown when no acceptable granule files are found in a CMN-R message
    '''
    def __init__(self):
        super().__init__(
            'Data file not found'
        )
