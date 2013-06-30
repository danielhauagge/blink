#!/usr/bin/env python

import logging
import urllib
import urllib2
import ConfigParser
import argparse
import json
import pymongo
import pymongo.errors
from itertools import islice

from common import *

def split_every(n, iterable):
    i = iter(iterable)
    piece = list(islice(i, n))
    while piece:
        yield piece
        piece = list(islice(i, n))

def search(api_key, query, tag):
    page = 1
    nPages = 1

    while page <= nPages:
        params = {
            'method'            :   'flickr.photos.search',
            'api_key'           :   api_key,
            'text'              :   query,
            'format'            :   'json',
            'nojsoncallback'    :   1,
            'page'              :   page,
            'per_page'          :   500,
            'extras'            :   'description,date_taken,owner_name,geo_tags',
        }
        r = urllib2.urlopen('http://api.flickr.com/services/rest/?%s'%urllib.urlencode(params))
        data = r.read()
        response = json.loads(data)
        nPages = response['photos']['pages']
        logging.info('Page %d/%d'%(page, nPages))
       
        assert response['photos']['page'] == page
 
        for photo in response['photos']['photo']:
            photo_obj = {
                '_id'                   :   photo['id'],
                'title'                 :   photo['title'],
                'owner'                 :   photo['owner'],
                'datetaken'             :   photo['datetaken'],
                'description'           :   photo['description'],
                'datetakengranularity'  :   photo['datetakengranularity'],
                'ownername'             :   photo['ownername'],
                'tag'                   :   tag,
            }
            yield photo_obj

        page += 1

def order(api_key, host, port, database, collection, query, tag):
    logging.info(query)

    client = pymongo.MongoClient(host, port)
    collection = client[database][collection]

    collection.create_index('filename')
    collection.create_index('exif')
    collection.create_index('width')
    collection.create_index('sift')
    collection.create_index('height')
    collection.create_index('camera')
    collection.create_index('sift_expires')
    collection.create_index('exif_expires')
    collection.create_index('photo_expires')
    collection.create_index('focal_hint_expires')
 
    for batch in split_every(500, search(api_key, query, tag)):
        try:
            collection.insert(batch, continue_on_error=True)
        except pymongo.errors.DuplicateKeyError:
            pass
   

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--query', required=True)
    parser.add_argument('--tag', required=True)
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

    order(api_key, host, port, database, collection, args.query, args.tag)
