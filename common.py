import random
import time
import logging
import datetime
# import argparse
import ConfigParser
from collections import namedtuple
from commands import getoutput
import os

LAST_FLICKR_TIME = datetime.datetime.now()



def get_aws_public_hostname():
    return getoutput('curl -s http://169.254.169.254/latest/meta-data/public-ipv4')
    # return getoutput('curl http://169.254.169.254/latest/meta-data/public-hostname')

def init_logger():
    '''Initialize the logger, call at the begining of main.
    '''
    logging.basicConfig(level=logging.INFO,
                        format='[Blink] %(asctime)s %(levelname)5s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.addLevelName(logging.WARNING, 'WARN')

def rate_limiter():
    global LAST_FLICKR_TIME

    second = datetime.timedelta(seconds=1)
    time_diff = datetime.datetime.now() - LAST_FLICKR_TIME
    if time_diff < second:
        wait_time = (second - time_diff).total_seconds()
        print('Rate limiting - sleeping %f seconds'%wait_time)
        time.sleep(wait_time)
    LAST_FLICKR_TIME = datetime.datetime.now()

class FlickrException(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code

def load_config():
    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser('~/.blink'))
    return config


def get_n_downloaded(collection):
    return collection.find({'filename': {'$exists': 'true'}}).count()

def remove_downloaded(collection):
    return collection.remove({'filename': {'$exists': 'true'}})

def get_n_urls(collection):
    return collection.count()

def expire(collection, key):
    collection.update(
        {key: {'$lt':datetime.datetime.now()}},
        {'$unset':{key:1}},
        multi=True,
    )

def checkout(collection, input_keys, expires_key):
    spec_input = {key:{'$exists':True} for key in input_keys}
    query = {
        '_id':{'$gte':str(random.randint(0, 100000))},
        expires_key : {'$lt':datetime.datetime.now()}
    }

    update = {'$set':{expires_key:datetime.datetime.now()+datetime.timedelta(minutes=10)}}

    """
    """
    entry = None
    while entry is None:
        entry = collection.find_one(
            query,
            fields=input_keys+['_id'],
        )
        query['_id'] = entry['_id']

        entry = collection.find_and_modify(
            query=query,
            update=update,
            fields=input_keys+['_id'],
        )
        del query['_id']
        if entry is None:
            print('retry')

    return entry

def checkin(collection, entry_id, outputs, expires_key):
    s = outputs
    s[expires_key] = datetime.datetime.fromtimestamp(100000000000)
    # print('start checkin')
    collection.update(
        {'_id':entry_id},
        {
            '$set':outputs,
        },
    )
    # print('end checkin')
