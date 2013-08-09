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
from Task import Task

class PhotoTask(Task):
    def _get_image_url(self, flickr_id):
        params = {
            'method'            :   'flickr.photos.getSizes',
            'api_key'           :   self.api_key,
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

    def _get_image(self, image_url):
        r = urllib2.urlopen(image_url)
        data = r.read()
        return data

    def next(self):
        self.entry = checkout(
            self.collection,
            [],
            ['filename'],
            'filename_expires',
        )

        return self.entry is not None

    def run(self):
        logging.info('START: %s filename'%self.entry['_id'])
        image_url, width, height = self._get_image_url(self.entry['_id'])
        image = self._get_image(image_url)
        k = Key(self.b)        
        k.key = os.path.join(self.collection.name, image_url.split('/')[-1])
        k.set_contents_from_string(image)
        k.set_acl('public-read')
        if height > width and height > 2400:
            resize_ratio = 2400.0/height
        elif height <= width and width > 2400:
            resize_ratio = 2400.0/width
        else:
            resize_ratio = 1

        checkin(
            self.collection,
            self.entry['_id'],
            {
                'filename':k.key,
                'width':int(resize_ratio*width),
                'height':int(resize_ratio*height),
            },
            'filename_expires',
        )
        logging.info('SUCCESS: %s filename'%self.entry['_id'])

        self.entry = None
