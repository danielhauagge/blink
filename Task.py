import logging

class Task (object):
    def __init__(self, api_key, bucket, collection):
        self.api_key = api_key
        self.bucket = bucket
        self.collection = collection
        self.entry = None

        self.logger = logging.getLogger(self.__class__.__name__)

    def next(self):
        raise NotImplementedException()

    def run(self):
        raise NotImplementedException()
