#!/usr/bin/env python

import gzip
import numpy
import siftfastpy
import Image
import tempfile
import os
import urllib
import urllib2
import json

from boto.s3.key import Key

from common import *
from Task import Task

class SiftTask (Task):
    def _sift_generator(self, frames, desc):
        yield '%d %d'%(desc.shape[0],desc.shape[1])
        for i in xrange(frames.shape[0]):
            yield '%d %d %f %f'%(frames[i,1],frames[i,0],frames[i,3],frames[i,2])
            s = ''
            for j,d in enumerate(desc[i]):
                s += str(min(255,int(d*512.0))) + ' '
                if j%16 == 15:
                    s += '\n'
            yield s

    def next (self):
        self.entry = checkout(
            self.collection,
            ['filename', 'width', 'height'],
            'sift_expires',
        )

        return self.entry is not None

    def run (self):
        self.logger.info('START: %s sift'%self.entry['_id'])
        kin = Key(self.bucket)
        kin.key = self.entry['filename']
        kout = Key(self.bucket)
        splitext = os.path.splitext(self.entry['filename'])
        kout.key = '%s.key.gz'%splitext[0]
        with tempfile.NamedTemporaryFile(suffix=splitext[1], delete=False) as f:
            kin.get_contents_to_file(f)
            f.close()
        try:
            im = Image.open(f.name)
        except IOError, e:
            self.logger.info('ERROR: %s %s sift'%(self.entry['_id'],e))
            return False
        finally:
            os.unlink(f.name)
        im = im.convert(mode='L')
        im.resize((self.entry['height'],self.entry['width']), Image.ANTIALIAS)
        siftimage = siftfastpy.Image(numpy.reshape(im.getdata(), im.size[::-1]))
        frames, desc = siftfastpy.GetKeypoints(siftimage)

        with tempfile.NamedTemporaryFile(suffix="key.gz", delete=False) as f:
            with gzip.open(f.name, 'wb') as g:
                for line in self._sift_generator(frames, desc):
                    g.write(line)
                    g.write('\n')
            kout.set_contents_from_file(f)
            kout.set_acl('public-read')
            os.unlink(f.name)

        checkin(
            self.collection,
            self.entry['_id'],
            {'sift':kout.key},
            'sift_expires',
        )
        self.logger.info('SUCCESS: %s sift'%self.entry['_id'])

