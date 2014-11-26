#!/usr/bin/env python

import os
import urllib
import urllib2
import json
from cStringIO import StringIO
# import Image
# from PIL import Image, ImageFile
# ImageFile.MAXBLOCK = 2**40

from wand.image import Image

from boto.s3.key import Key

from common import *

from Task import Task

def image_to_string(img):
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix = '.jpg', delete = False)
    print tmp.name
    img.save(tmp)
    return open(tmp.name, 'rb').read()

class PhotoTask(Task):
    def _get_image_url(self, entry):
        if 'url' in entry: return entry['url'], None, None

        flickr_id = entry['_id']

        params = {
            'method'            :   'flickr.photos.getSizes',
            'api_key'           :   self.api_key,
            'format'            :   'json',
            'nojsoncallback'    :   1,
            'photo_id'          :   flickr_id,
        }

        if self.rate_limit:
            rate_limiter()

        r = urllib2.urlopen('https://api.flickr.com/services/rest/?%s'%urllib.urlencode(params))
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
            ['url'],
            'filename_expires',
        )

        return self.entry is not None

    def run(self):
        self.logger.info('START: %s filename'%self.entry['_id'])
        try:
            image_url, _, _ = self._get_image_url(self.entry)
            print image_url
            image =  Image(blob = self._get_image(image_url))
            image.format = 'jpeg'

            width = image.width
            height = image.height

            # if height > width and height > 2400:
            #     resize_ratio = 2400.0/height
            # elif height <= width and width > 2400:
            #     resize_ratio = 2400.0/width
            # else:
            resize_ratio = 1

            TARGET_SIZE = 512
            if min(width, height) > TARGET_SIZE:
                scale = max(float(TARGET_SIZE)/width, float(TARGET_SIZE)/height)
                image.resize(int(round(width * scale)), int(round(height * scale)))
                width = image.width
                height = image.height
                print 'width x height', width, 'x', height

                # image = img_tmp.convert('RGB').tostring('jpeg', 'RGB', 0, 1)

            k = Key(self.bucket)

            # Certain photo sizes have this query string at the end
            k.key = os.path.join(self.collection.name, image_url.split('/')[-1].replace('?zz=1', ''))
            k.set_contents_from_string(image.make_blob())
            k.set_acl('public-read')

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
        except FlickrException, exc:
            # Some errors should be hidden
            # I think the only cases we don't want to handle are permission denied and photo not found
            # I'm unsure of photo not found though.  Could be a transient error, but could also be that the user took down the photo.
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
            }[exc.code]

            if hide_error:
                checkin(
                    self.collection,
                    self.entry['_id'],
                    {
                        'filename':'',
                        'width':0,
                        'height':0,
                    },
                    'filename_expires',
                )
            else:
                raise

        self.logger.info('SUCCESS: %s filename'%self.entry['_id'])

        self.entry = None
