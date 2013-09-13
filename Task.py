import logging

class Task (object):
    def __init__(self, api_key, b, collection):
        self.api_key = api_key
        self.b = b
        self.collection = collection
        self.entry = None

        self.logger = logging.getLogger(self.__class__.__name__)

    def next(self):
        raise NotImplementedException()

    def run(self):
        raise NotImplementedException()
