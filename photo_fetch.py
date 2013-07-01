#!/usr/bin/env python

import os
import datetime
import urllib
import urllib2
import json
import logging

import pymongo
from boto.s3.connection import S3Connection
from boto.s3.key import Key

from common import *

def get_image_url(api_key, flickr_id):
    params = {
        'method'            :   'flickr.photos.getSizes',
        'api_key'           :   api_key,
        'format'            :   'json',
        'nojsoncallback'    :   1,
        'photo_id'          :   flickr_id,
    }
    r = urllib2.urlopen('http://api.flickr.com/services/rest/?%s'%urllib.urlencode(params))
    data = r.read()
    response = json.loads(data)

    if response['stat'] == 'fail':
        raise FlickrException(response['code'], response['message'])

    sizes = {int(entry['width'])*int(entry['height']):(entry['source'],int(entry['width']),int(entry['height'])) for entry in response['sizes']['size'] if entry['media'] == 'photo'}
    max_size = max(sizes.keys())
    return sizes[max_size]    

def get_image(image_url):
    r = urllib2.urlopen(image_url)
    data = r.read()
    return data



def photo_fetch(collection, b, api_key, **kwargs):
    expire(collection, 'filename_expires')

    entry = checkout(
        collection,
        [],
        ['filename'],
        'filename_expires',
    )

    if entry is not None:
        logging.info('START: %s filename'%entry['_id'])
        try:
            image_url, width, height = get_image_url(api_key, entry['_id'])
            image = get_image(image_url)
            k = Key(b)        
            k.key = os.path.join(collection.name, image_url.split('/')[-1])
            k.set_contents_from_string(image)
            k.set_acl('public-read')
            if height > width and height > 2400:
                resize_ratio = 2400.0/height
            elif height <= width and width > 2400:
                resize_ratio = 2400.0/width
            else:
                resize_ratio = 1

            checkin(
                collection,
                entry['_id'],
                {
                    'filename':k.key,
                    'width':int(resize_ratio*width),
                    'height':int(resize_ratio*height),
                },
                'filename_expires',
            )
            logging.info('SUCCESS: %s filename'%entry['_id'])
            return True
        except FlickrException, e:
            logging.info('ERROR: %s %s'%(entry['_id'],e))
    return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    config = load_config()

    client = pymongo.MongoClient(config.host, config.port)
    collection = client[config.database][config.collection]

    s3conn = S3Connection(config.aws_key, config.aws_secret)
    b = s3conn.get_bucket(config.bucket)


    photo_fetch(collection, b, config.api_key)
