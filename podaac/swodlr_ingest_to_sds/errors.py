'''swodlr-ingest-to-sds specific errors'''

class DataNotFoundError(RuntimeError):
  def __init__(self):
    super().__init__(
      'Data file not found'
    )
