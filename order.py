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

def search(api_key, query, tag, date_min, date_max):
    page = 1
    nPages = 1

    previous_count = 0
    ids = set()

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
            #'license'           :   '4,7',
            'privacy_filter'    :   1,
            'safe_search'       :   3,
            'content_type'      :   6,
        }
        if date_min is not None:
            params['min_taken_date'] = date_min
        if date_max is not None:
            params['max_taken_date'] = date_max
        r = urllib2.urlopen('http://api.flickr.com/services/rest/?%s'%urllib.urlencode(params))
        data = r.read()
        response = json.loads(data)

        if response['stat'] == 'fail':
            raise FlickrException(response['code'], response['message'])

        nPages = response['photos']['pages']
        logging.info('Page %d/%d'%(page, nPages))
       
        assert response['photos']['page'] == page
 
        for photo in response['photos']['photo']:
            ids.add(photo['id'])
            photo_obj = {
                '_id'                   :   photo['id'],
                'title'                 :   photo['title'],
                'owner'                 :   photo['owner'],
                'datetaken'             :   photo['datetaken'],
                'description'           :   photo['description']['_content'],
                'datetakengranularity'  :   photo['datetakengranularity'],
                'ownername'             :   photo['ownername'],
                'tag'                   :   tag,
            }
            yield photo_obj

        logging.info('%d files'%len(ids))
        if len(ids) == previous_count:
            logging.info('No more photos found')
            return

        previous_count = len(ids)

        page += 1

def order(api_key, host, port, database, collection, query, tag, min_date, max_date):
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
 
    try:
        for batch in split_every(500, search(api_key, query, tag, min_date, max_date)):
            try:
                logging.info('%d entries'%len(batch))
                collection.insert(batch, continue_on_error=True)
            except pymongo.errors.DuplicateKeyError:
                pass
    except FlickrException, e:
        logging.info('ERROR: %s'%e) 

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--query', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--min-date')
    parser.add_argument('--max-date')
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

    order(api_key, host, port, database, collection, args.query, args.tag, args.min_date, args.max_date)
