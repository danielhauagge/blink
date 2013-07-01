#!/usr/bin/env python

import gzip
import numpy
import siftfastpy
import Image
import tempfile
import os
import datetime
import urllib
import urllib2
import json
import logging

from boto.s3.connection import S3Connection
from boto.s3.key import Key
import pymongo

from common import *

def sift_generator(frames, desc):
    yield '%d %d'%(desc.shape[0],desc.shape[1])
    for i in xrange(frames.shape[0]):
        yield '%d %d %f %f'%(frames[i,1],frames[i,0],frames[i,3],frames[i,2])
        s = ''
        for j,d in enumerate(desc[i]):
            s += str(min(255,int(d*512.0))) + ' '
            if j%16 == 15:
                s += '\n'
        yield s

def sift_compute(collection, b, **kwargs):
    expire(collection, 'sift_expires')

    entry = checkout(
        collection,
        ['filename', 'width', 'height'],
        ['sift'],
        'sift_expires',
    )

    if entry is not None:
        logging.info('START: %s sift'%entry['_id'])
        kin = Key(b)
        kin.key = entry['filename']
        kout = Key(b)
        splitext = os.path.splitext(entry['filename'])
        kout.key = '%s.key.gz'%splitext[0]
        with tempfile.NamedTemporaryFile(suffix=splitext[1], delete=False) as f:
            kin.get_contents_to_file(f)
            f.close()
        try:
            im = Image.open(f.name)
        except IOError, e:
            logging.info('ERROR: %s %s sift'%(entry['_id'],e))
            return False
        finally:
            os.unlink(f.name)
        im = im.convert(mode='L')
        im.resize((entry['height'],entry['width']), Image.ANTIALIAS)
        siftimage = siftfastpy.Image(numpy.reshape(im.getdata(), im.size[::-1]))
        frames, desc = siftfastpy.GetKeypoints(siftimage)

        with tempfile.NamedTemporaryFile(suffix="key.gz", delete=False) as f:
            with gzip.open(f.name, 'wb') as g:
                for line in sift_generator(frames, desc):
                    g.write(line)
                    g.write('\n')
            kout.set_contents_from_file(f)
            kout.set_acl('public-read')
            os.unlink(f.name)

        checkin(
            collection,
            entry['_id'],
            {'sift':kout.key},
            'sift_expires',
        )
        logging.info('SUCCESS: %s sift'%entry['_id'])
        return True
    return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    config = load_config()

    client = pymongo.MongoClient(config.host, config.port)
    collection = client[config.database][config.collection]

    s3conn = S3Connection(config.aws_key, config.aws_secret)
    b = s3conn.get_bucket(config.bucket)

    sift_compute(collection, b)
