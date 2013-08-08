class Task:
    def __init__(self, api_key, b, collection):
        self.api_key = api_key
        self.b = b
        self.collection = collection
        self.entry = None

    def next(self):
        raise NotImplementedException()

    def run(self):
        raise NotImplementedException()

    def expire(self):
        raise NotImplementedException()
