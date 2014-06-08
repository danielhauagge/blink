import time
import logging
import datetime
import argparse
import ConfigParser
from collections import namedtuple

LAST_FLICKR_TIME = datetime.datetime.now()

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

Config = namedtuple(
        'Config',
        'api_key,host,port,database,collection,aws_key,aws_secret,bucket,tasks,email,log,rate_limit',
)
        
def load_config():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--log', default='WARNING')
    args = parser.parse_args()

    config = ConfigParser.ConfigParser()
    if args.config is None:
        config.read('blink.cfg')
    else:
        config.read(args.config)

    api_key = config.get('flickr', 'api_key')
    rate_limit = config.getboolean('flickr', 'rate_limit')

    host = config.get('mongodb', 'host')
    port = config.getint('mongodb', 'port')
    database = config.get('mongodb', 'database')
    collection = config.get('mongodb', 'collection')

    aws_key = config.get('aws', 'aws_key')
    aws_secret = config.get('aws', 'aws_secret')
    bucket = config.get('aws', 'bucket')

    tasks = config.get('workers', 'tasks').split(',')

    email = config.get('admin', 'email')

    return Config(
        api_key=api_key,
        host=host,
        port=port,
        database=database,
        collection=collection,
        aws_key=aws_key,
        aws_secret=aws_secret,
        bucket=bucket,
        tasks=tasks,
        email=email,
        log=args.log,
        rate_limit=rate_limit,
    )

def expire(collection, key):
    collection.update(
        {key: {'$lt':datetime.datetime.now()}},
        {'$unset':{key:1}},
        multi=True,
    )

def checkout(collection, input_keys, expires_key): 
    spec_input = {key:{'$exists':True} for key in input_keys}
    query = {expires_key : {'$lt':datetime.datetime.now()}}

    update = {'$set':{expires_key:datetime.datetime.now()+datetime.timedelta(minutes=10)}}

    """
    entry = collection.find_and_modify(
        query,
        update=update,
        fields=input_keys+['_id'],
    )
    """
    entry = collection.find_one(
        query,
        fields=input_keys+['_id'],
    )

    return entry

def checkin(collection, entry_id, outputs, expires_key):
    s = outputs
    s[expires_key] = datetime.datetime.fromtimestamp(100000000000)
    collection.update(
        {'_id':entry_id},
        {
            '$set':outputs,
        }
    )

