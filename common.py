import logging
import datetime
import argparse
import ConfigParser
from collections import namedtuple

class FlickrException(Exception): 
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code

Config = namedtuple(
        'Config',
        'api_key,host,port,database,collection,aws_key,aws_secret,bucket,tasks',
)
        
def load_config():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    args = parser.parse_args()

    config = ConfigParser.ConfigParser()
    if args.config is None:
        config.read('blink.cfg')
    else:
        config.read(args.config)

    api_key = config.get('flickr', 'api_key')

    host = config.get('mongodb', 'host')
    port = config.getint('mongodb', 'port')
    database = config.get('mongodb', 'database')
    collection = config.get('mongodb', 'collection')

    aws_key = config.get('aws', 'aws_key')
    aws_secret = config.get('aws', 'aws_secret')
    bucket = config.get('aws', 'bucket')

    tasks = config.get('workers', 'tasks').split(',')

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

    entry = collection.find_and_modify(
        query,
        update=update,
        fields=input_keys+['_id'],
    )

    return entry

def checkin(collection, entry_id, outputs, expires_key):
    collection.update(
        {'_id':entry_id},
        {
            '$set':outputs,
            '$set':{expires_key:datetime.datetime.fromtimestamp(100000000000)},
        }
    )

