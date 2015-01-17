#!/usr/bin/env python

import gevent
from gevent import monkey; monkey.patch_all()

import multiprocessing
from boto.s3.connection import S3Connection
import pymongo

import logging
import time
import os
import socket
import sys
from collections import namedtuple
import argparse

from common import *

# ------------------------------------------------------------------------------
# Globals
# ------------------------------------------------------------------------------

TaskEntry = namedtuple('TaskEntry', 'task,timer')

config = load_config()

init_logger()
# logging.basicConfig(level=getattr(logging, config.log.upper()))
logger = logging.getLogger('fetch')

# -------------
# MongoDB
# -------------
# mongodb_hostname = '%s:%s'%(config.get('mongodb','host'), config.get('mongodb','port'))
# logger.info('MongoDB host: %s', mongodb_hostname)
# mongodb_client = pymongo.MongoClient(mongodb_hostname, auto_start_request=False, max_pool_size=None,
#     read_preference=pymongo.read_preferences.ReadPreference.PRIMARY_PREFERRED)

# logger.info('MongoDB database: %s:%s', config.get('mongodb','database'), config.get('mongodb','collection'))
collection = None #mongodb_client[config.get('mongodb','database')][config.get('mongodb','collection')]
mongodb_hostname = None

# -------------
# AWS
# -------------
logging.info('Conecting to AWS services')
s3conn = S3Connection(config.get('aws', 'aws_key'), config.get('aws','aws_secret'))
bucket = s3conn.get_bucket(config.get('aws', 'bucket'))

# -------------
# Flickr
# -------------
api_key = config.get('flickr','api_key')
rate_limit = config.get('flickr','rate_limit')

# -------------
# Misc
# -------------
max_images = -1

# ------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------
def build_task(task, **kwargs):
    # print('Importing %s'%task)
    module = __import__(task)
    c = getattr(module, task)
    return c(**kwargs)

def run():
    task_entries = [
        TaskEntry(
            task=build_task(
                t,
                collection=collection,
                bucket=bucket,
                api_key=api_key,
                rate_limit=rate_limit,
                db_hostname=mongodb_hostname
            ),
            timer=pos
        )
    for pos, t in enumerate(config.get('workers','tasks').split(','))]

    try:
        while True:
            n_downloaded = get_n_downloaded(collection)
            if n_downloaded > max_images:
                logging.info('Dowloaded enough images %d, quitting for now'%(n_downloaded))
                sys.exit(1)


            task_entries.sort(key=lambda k: k.timer)

            # sleep until the earliest task is ready
            sleep_time = task_entries[0].timer-1
            if sleep_time > 0:
                logger.info('sleeping %d seconds', sleep_time)
                time.sleep(sleep_time)
            # Update task timers
            task_entries = [
                TaskEntry(
                    task=t.task,
                    timer=max(0,t.timer-sleep_time-1))
            for t in task_entries]

            task_entry = task_entries[0]

            assert task_entry.timer == 0
            # assume the task will be successful and stick it in the first empty slot in line
            for i in xrange(1, len(task_entries[1:])):
                if task_entries[i].timer > i:
                    task_entries[0] = TaskEntry(
                        task=task_entry.task,
                        timer=i,
                    )

            if task_entries[0].timer == 0:
                task_entries[0] = TaskEntry(
                    task=task_entry.task,
                    timer=len(task_entries),
                )

            try:
                # if the task has work to do, do it
                # logging.info(task_entry.task)
                if task_entry.task.next():
                    task_entry.task.run()

                # otherwise stick it even further back in the line
                else:
                    logger.info('Postponing: %s', task_entry.task.__class__.__name__)
                    task_entries[0] = TaskEntry(
                        task=task_entry.task,
                        timer=task_entry.timer+2*len(task_entries)
                    )

            # log transient errors locally
            except Exception, exc:
                pass
                #logger.info('%s: %s', task_entry.task.__class__.__name__, exc)
    except KeyboardInterrupt:
        pass

    # send me an email if the script dies
    except Exception:
        raise

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
if __name__ == '__main__':

    # Parse command line options
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-hostname', required = True)
    parser.add_argument('--collection', required = True)
    parser.add_argument('--max-images', type = int, default = -1, help = 'Process kills itself after this amount of images has been downloaded')
    args = parser.parse_args()

    max_images = args.max_images

    # Get connection with database
    mongodb_hostname = args.db_hostname
    mongodb_url = '%s:%s'%(mongodb_hostname, config.get('mongodb','port'))
    logger.info('MongoDB host: %s', mongodb_url)
    mongodb_client = pymongo.MongoClient(mongodb_url, auto_start_request=False, max_pool_size=None,
        read_preference=pymongo.read_preferences.ReadPreference.PRIMARY_PREFERRED)

    logger.info('MongoDB database: %s:%s', config.get('mongodb','database'), args.collection)
    collection = mongodb_client[config.get('mongodb','database')][args.collection]

    # Run
    run()
    exit()
    logging.info('Spawning threads')
    threads = [gevent.spawn(run) for _ in xrange(multiprocessing.cpu_count() * 8)]

    gevent.joinall(threads)
