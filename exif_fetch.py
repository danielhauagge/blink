#!/usr/bin/env python

import datetime
import urllib
import urllib2
import json
import logging

import pymongo

from common import *

def get_exif(api_key, flickr_id):
    params = {
        'method'            :   'flickr.photos.getExif',
        'api_key'           :   api_key,
        'format'            :   'json',
        'nojsoncallback'    :   1,
        'photo_id'          :   flickr_id,
    }
    r = urllib2.urlopen('http://api.flickr.com/services/rest/?%s'%urllib.urlencode(params))
    data = r.read()
    response = json.loads(data)
    if response['stat'] == 'fail':
        # Some errors should be hidden
        # I think the only case we don't want to handle is permission denied
        hide_error = {
            1: False, # photo not found
            2: True, # permission denied
            100: False, # invalid api key
            105: False, # service currently unavailable
            111: False, # format "xxx" not found
            112: False, # method "xxx" not found
            114: False, # invalid soap envelope
            115: False, # invalid xml-rpc method call
            116: False, # bad url found
        }[response['code']]
            
        if hide_error:
            return {}, ''

        raise FlickrException(response['code'], response['message'])
    tags = {str(tag['tag']):tag['raw']['_content'] for tag in response['photo']['exif']}
    return tags, response['photo']['camera']



def exif_fetch(api_key, collection, **kwargs):
    expire(collection, 'exif_expires')

    entry = checkout(
        collection,
        [],
        ['exif', 'camera'],
        'exif_expires',
    )

    if entry is not None:
        try:
            logging.info('START: %s exif'%entry['_id'])
            exif, camera = get_exif(api_key, entry['_id'])

            checkin(
                collection,
                entry['_id'],
                {
                    'exif':exif, 
                    'camera':camera,
                },
                'exif_expires',
            )
            logging.info('SUCCESS: %s exif'%entry['_id'])
            return True
        except FlickrException, e:
            logging.info('ERROR: %s %s exif'%(entry['_id'],e))
    return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    config = load_config()

    client = pymongo.MongoClient(config.host, config.port)
    collection = client[config.database][config.collection]

    exif_fetch(config.api_key, collection)
