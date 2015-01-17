import logging

class Task (object):
    def __init__(self, api_key, bucket, collection, rate_limit, db_hostname):
        self.api_key = api_key
        self.bucket = bucket
        self.collection = collection
        self.rate_limit = rate_limit
        self.db_hostname = db_hostname
        self.entry = None

        self.logger = logging.getLogger(self.__class__.__name__)

    def next(self):
        raise NotImplementedException()

    def run(self):
        raise NotImplementedException()
