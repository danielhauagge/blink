#!/usr/bin/env python

import datetime
import logging
import urllib
import urllib2
import ConfigParser
import argparse
import json
import pymongo
import pymongo.errors
from itertools import islice
import Queue
import time
from os import path
from urlparse import urlparse
import sys

from common import *
init_logger()

def split_every(n, iterable):
    i = iter(iterable)
    piece = list(islice(i, n))
    while piece:
        yield piece
        piece = list(islice(i, n))

def get_id_from_url(url):
    fname = path.basename(urlparse(url).path)
    return fname.split('_')[0]

def get_urls_from_file(fname, tag):
    urls = open(fname).read().strip().split('\n')
    logging.info('%d URLs in the file', len(urls))

    epoch = datetime.datetime.fromtimestamp(0)

    for url in urls:

        photo_obj = {
            '_id'                   :   get_id_from_url(url),
            'tag'                   :   tag,
            'url'                   :   url,
            'filename_expires'      :   epoch,
            'sift_expires'          :   epoch,
            'exif_expires'          :   epoch,
            'focal_hint_expires'    :   epoch,
        }
        yield photo_obj

def search(api_key, query, tag, date_min, date_max):
    if date_min is not None:
        date_min = datetime.datetime.strptime(date_min, '%Y-%m-%d')
    if date_max is not None:
        date_max = datetime.datetime.strptime(date_max, '%Y-%m-%d')

    date_ranges = Queue.Queue()
    date_ranges.put((date_min, date_max))

    while not date_ranges.empty():
        date_range = date_ranges.get()
        logging.info('Date range: %s to %s'%date_range)

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
                #'license'           :   '4,7',
                'privacy_filter'    :   1,
                'safe_search'       :   3,
                'content_type'      :   6,
            }
            if date_min is not None:
                params['min_taken_date'] = date_range[0]
            if date_max is not None:
                params['max_taken_date'] = date_range[1]
            try:
                logging.info('Requesting page %d (%s - %s)'%(page, date_range[0], date_range[1]))
                #rate_limiter()
                r = urllib2.urlopen('https://api.flickr.com/services/rest/?%s'%urllib.urlencode(params))
                data = r.read()
            except Exception, exc:
                logging.info('Error: %s'%exc)
                time.sleep(10)
                continue
            response = json.loads(data)

            logging.info(response['stat'])

            if response['stat'] == 'fail':
                raise FlickrException(response['code'], response['message'])

            if response['photos']['pages'] == 0:
                logging.info("response['photos']['pages'] == 0, sleeping for 10 sec")
                time.sleep(10)
                continue

            nPages = response['photos']['pages']

            if nPages > 7 and date_range[0] is not None and date_range[1] is not None:
                logging.info('Too many pages.  Splitting date range.')
                mid = (date_range[1] - date_range[0])/2 + date_range[0]
                date_ranges.put((date_range[0], mid))
                date_ranges.put((mid, date_range[1]))
                nPages = 0
                continue


            logging.info('Page %d/%d, %d urls', page, nPages, len(response['photos']['photo']))

            # Apparently this can't be trusted
            #assert response['photos']['page'] == page

            epoch = datetime.datetime.fromtimestamp(0)

            for photo in response['photos']['photo']:
                try:
                    photo_obj = {
                        '_id'                   :   photo['id'],
                        'title'                 :   photo['title'],
                        'owner'                 :   photo['owner'],
                        'datetaken'             :   datetime.datetime.strptime(photo['datetaken'], '%Y-%m-%d %H:%M:%S'),
                        'description'           :   photo['description']['_content'],
                        'datetakengranularity'  :   photo['datetakengranularity'],
                        'ownername'             :   photo['ownername'],
                        'tag'                   :   tag,
                        'filename_expires'      :   epoch,
                        'sift_expires'          :   epoch,
                        'exif_expires'          :   epoch,
                        'focal_hint_expires'    :   epoch,
                    }
                    yield photo_obj
                except Exception, exc:
                    logging.info(exc)

            page += 1

def order(api_key, host, port, database, collection, query, tag, min_date, max_date, urls_fname, max_images):
    # logging.info(query)

    client = pymongo.MongoClient(host, port)
    collection = client[database][collection]

    # help(collection)
    try:
        if query != None: get_next = search(api_key, query, tag, min_date, max_date)
        elif urls_fname != None: get_next = get_urls_from_file(urls_fname, tag)
        else: assert(False)

        for batch in split_every(5, get_next):
            if max_images > 0:
                # n_downloaded = get_n_downloaded(collection)
                n_urls = get_n_urls(collection)
                if n_urls > max_images:
                    logging.info('Got enough image urls: %d, quitting now'%(n_urls))
                    sys.exit(1)

            try:
                collection.insert(batch, continue_on_error = True)
            except pymongo.errors.DuplicateKeyError:
                pass


    except FlickrException, e:
        logging.info('ERROR: %s'%e)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--query')
    parser.add_argument('--urls')
    parser.add_argument('--tag', default='tag') # dh: not sure what this is useful for
    parser.add_argument('--min-date')
    parser.add_argument('--max-date')
    parser.add_argument('--collection')
    parser.add_argument('--max-images', type = int, default = -1, help = 'Process kills itself after this amount of images has been downloaded')
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

    order(api_key, host, port, database, collection, args.query, args.tag,
        args.min_date, args.max_date, args.urls, args.max_images)
