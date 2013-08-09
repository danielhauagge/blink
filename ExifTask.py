#!/usr/bin/env python

import datetime
import urllib
import urllib2
import json
import logging

import pymongo

from common import *
from Task import Task

class ExifTask(Task):
    def _get_exif(self, flickr_id):
        params = {
            'method'            :   'flickr.photos.getExif',
            'api_key'           :   self.api_key,
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
                1: True, # photo not found
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

    def next(self):
        self.entry = checkout(
            self.collection,
            [],
            'exif_expires',
        )

        return self.entry is not None

    def run(self):
        logging.info('START: %s exif'%self.entry['_id'])
        exif, camera = self._get_exif(self.entry['_id'])

        checkin(
            self.collection,
            self.entry['_id'],
            {
                'exif':exif, 
                'camera':camera,
            },
            'exif_expires',
        )
        logging.info('SUCCESS: %s exif'%self.entry['_id'])

        self.entry = None

