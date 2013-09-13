#!/usr/bin/env python

import datetime
import urllib
import urllib2
import json

import pymongo

from common import *

from Task import Task

class FocalTask (Task):
    def __init__ (self, *args, **kwargs):
        super(FocalTask, self).__init__ (*args, **kwargs) 

        with open('cameras.json', 'r') as f:
            self.ccd_widths = json.load(f)

    def next (self):
        self.entry = checkout(
            self.collection, 
            ['exif', 'width', 'height', 'camera'],
            'focal_hint_expires',
        )

        return self.entry is not None

    def run (self):
        self.logger.info('START: %s focal'%self.entry['_id'])

        exif = self.entry['exif']
        make = exif.get('Make', None)
        model = exif.get('Model', None)
        focal_length = exif.get('FocalLength', None)
        focal_mm = None
        if focal_length is not None:
            focal_mm = float(focal_length.split()[0])
        self.logger.info('Focal mm: %s'%focal_mm)

        make_model = '%s %s'%(make, model)
        make_model = make_model.strip()
        make_model = ' '.join(make_model.split())
        self.logger.info('EXIF make model: %s'%make_model)
        ccd_width = self.ccd_widths.get(make_model, None)
        self.logger.info('CCD width: %s'%ccd_width)

        digital_zoom = exif.get('DigitalZoomRatio', '')
        if digital_zoom not in ('', 'undef'):
            digital_zoom = float(digital_zoom.split()[0])
        else:
            digital_zoom = 1
        if digital_zoom == 0:
            digital_zoom = 1
        self.logger.info('Digital zoom: %s'%digital_zoom)

        if focal_mm is not None:
            focal_mm *= digital_zoom
        self.logger.info('Focal mm zoomed: %s'%focal_mm)

        if focal_mm is None or ccd_width is None:
            focal_pixels = None
        else:
            width = self.entry['width']
            height = self.entry['height']

            if width < height:
                width, height = height, width

            focal_pixels = width * (focal_mm/ccd_width)

        self.logger.info('Focal pixels: %s'%focal_pixels)

        checkin(
            self.collection,
            self.entry['_id'],
            {'focal_hint':focal_pixels},
            'focal_hint_expires',
        )
        self.logger.info('SUCCESS: %s focal'%self.entry['_id'])

        self.entry = None

