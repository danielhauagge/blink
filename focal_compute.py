#!/usr/bin/env python

import datetime
import urllib
import urllib2
import json
import logging

import pymongo

from common import *

with open('cameras.json', 'r') as f:
    ccd_widths = json.load(f)

focal_plane_resolution_unit_converter = {
    'inches': 25.4,
    'cm': 10,
    'mm': 1,
    'um': 0.001,
}

def focal_compute(collection, **kwargs):
    expire(collection, 'focal_hint_expires')

    entry = checkout(
        collection, 
        ['exif', 'width', 'height', 'camera'],
        ['focal_hint'], 
        'focal_hint_expires',
    )

    if entry is not None:
        logging.info('START: %s focal'%entry['_id'])
        exif = entry['exif']
        make = exif.get('Make', None)
        model = exif.get('Model', None)
        focal_length = exif.get('FocalLength', None)
        focal_mm = None
        if focal_length is not None:
            focal_mm = float(focal_length.split()[0])
        logging.info('Focal mm: %s'%focal_mm)
        focal_plane_xres = exif.get('FocalPlaneXResolution', None)
        if focal_plane_xres is not None:
            focal_plane_xres = float(focal_plane_xres)
        exif_image_width = exif.get('ExifImageWidth', None)
        focal_plane_resolution_unit = exif.get('FocalPlaneResolutionUnit', None)
        focal_plane_units = focal_plane_resolution_unit_converter.get(focal_plane_resolution_unit, None)
        ccd_width_exif = None
        if focal_plane_xres is not None and exif_image_width is not None:
            ccd_width_exif = exif_image_width*focal_plane_units/focal_plane_xres;
        logging.info('CCD width EXIF: %s'%ccd_width_exif)

        make_model = '%s %s'%(make, model)
        make_model = make_model.strip()
        make_model = ' '.join(make_model.split())
        logging.info('EXIF make model: %s'%make_model)
        logging.info('Flickr make model: %s'%entry['camera'])
        ccd_width_prior = ccd_widths.get(make_model, None)
        logging.info('CCD width prior: %s'%ccd_width_prior)

        ccd_width = None
        if ccd_width_prior is not None and ccd_width_exif is not None:
            if ccd_width_prior > ccd_width_exif and (ccd_width_prior - ccd_width_exif)/ccd_width_prior < 0.2:
                ccd_width = ccd_width_exif
            else:
                ccd_width = ccd_width_prior
        elif ccd_width_prior is not None:
            ccd_width = ccd_width_prior
        elif ccd_width_exif is not None:
            ccd_width = ccd_width_exif
        logging.info('CCD width: %s'%ccd_width)

        digital_zoom = exif.get('DigitalZoomRatio', None)
        if digital_zoom is not None and digital_zoom != 'undef':
            digital_zoom = float(digital_zoom.split()[0])
        if digital_zoom == 0 or digital_zoom is None:
            digital_zoom = 1
        logging.info('Digital zoom: %s'%digital_zoom)

        if focal_mm is not None:
            focal_mm *= digital_zoom
        logging.info('Focal mm zoomed: %s'%focal_mm)

        if focal_mm is None or ccd_width is None:
            focal_pixels = None
        else:
            width = entry['width']
            height = entry['height']

            if width < height:
                width, height = height, width

            focal_pixels = width * (focal_mm/ccd_width)

        logging.info('Focal pixels: %s'%focal_pixels)

        checkin(
            collection,
            entry['_id'],
            {'focal_hint':focal_pixels},
            'focal_hint_expires',
        )
        logging.info('SUCCESS: %s focal'%entry['_id'])
        return True

    return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    config = load_config()

    client = pymongo.MongoClient(config.host, config.port)
    collection = client[config.database][config.collection]

    focal_compute(collection)
