#!/usr/bin/env python

from boto.s3.connection import S3Connection
import pymongo

import itertools
import multiprocessing
import logging
import time
import socket

from exif_fetch import exif_fetch
from photo_fetch import photo_fetch
from sift_compute import sift_compute
from focal_compute import focal_compute

from common import *

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    config = load_config()

    client = pymongo.MongoClient(config.host, config.port)
    collection = client[config.database][config.collection]

    s3conn = S3Connection(config.aws_key, config.aws_secret)
    b = s3conn.get_bucket(config.bucket)
    api_key = config.api_key

    def task_generator():
        tasks = [
            focal_compute, 
            exif_fetch, 
            photo_fetch, 
            sift_compute,
        ]

        while True:
            for task in tasks:
                yield task

    def closure(task):
        try:
            task(collection=collection, b=b, api_key=api_key)
        except KeyboardInterrupt:
            pass

    pool = multiprocessing.Pool()
    gen = task_generator()
    N = 16 
    try:
        while True:
            g = pool.map(closure, itertools.islice(gen, N));
            if not any(g):
                time.sleep(2)
    except KeyboardInterrupt:
        logging.info('Terminating manager')
