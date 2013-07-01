#!/usr/bin/env python

from boto.s3.connection import S3Connection
import pymongo

import multiprocessing
import logging
import time
import socket

from exif_fetch import exif_fetch
from photo_fetch import photo_fetch
from sift_compute import sift_compute
from focal_compute import focal_compute

from common import *

def poll(idx, api_key, host, port, database, collection, aws_key, aws_secret, bucket):
    logging.info(idx)
    client = pymongo.MongoClient(host, port)
    collection = client[database][collection]

    s3conn = S3Connection(aws_key, aws_secret)
    b = s3conn.get_bucket(bucket)

    tasks = [
        focal_compute, 
        exif_fetch, 
        photo_fetch, 
        sift_compute,
    ]

    while True:
        try:
            fast = False
            for task in tasks:
		try:
                	fast |= task(collection=collection, b=b, api_key=api_key)
		except socket.error, e:
			logging.info('ERROR: %s %d'%(e,idx))
                    
            if not fast:
                logging.info('sleep')
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info('Terminating polling loop %d'%idx)
            break

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    config = load_config()

    def closure(idx):
        poll(
            idx,
            config.api_key,
            config.host, 
            config.port, 
            config.database, 
            config.collection, 
            config.aws_key, 
            config.aws_secret, 
            config.bucket
        )

    n = 2*multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=n)
    try:
        pool.map(closure, xrange(n))
    except KeyboardInterrupt:
        logging.info('Terminating manager')
