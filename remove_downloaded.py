#!/usr/bin/env python

import argparse
from common import *
from os import path
import pymongo
import pymongo.errors

init_logger()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--collection')
    args = parser.parse_args()

    config = ConfigParser.ConfigParser()
    if args.config is None:
        config.read(path.expanduser('~/.blink'))
    else:
        config.read(args.config)

    api_key = config.get('flickr', 'api_key')

    host = get_aws_public_hostname()
    port = config.getint('mongodb', 'port')
    database = config.get('mongodb', 'database')
    collection = args.collection

    client = pymongo.MongoClient(host, port)
    collection = client[database][collection]

    remove_downloaded(collection)
