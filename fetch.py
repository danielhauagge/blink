#!/usr/bin/env python

from boto.s3.connection import S3Connection
import pymongo

import logging
import time
from email.mime.text import MIMEText
import os
import socket
from collections import namedtuple

from common import *

def build_task(task, **kwargs):
    print('Importing %s'%task)
    module = __import__(task)
    c = getattr(module, task)
    return c(**kwargs)

TaskEntry = namedtuple('TaskEntry', 'task,timer')

if __name__ == '__main__':
    config = load_config()

    logging.basicConfig(level=getattr(logging, config.log.upper()))
    logger = logging.getLogger('fetch')

    client = pymongo.MongoClient(config.host, config.port)
    collection = client[config.database][config.collection]

    s3conn = S3Connection(config.aws_key, config.aws_secret)
    b = s3conn.get_bucket(config.bucket)
    api_key = config.api_key

    task_entries = [
        TaskEntry(
            task=build_task(t, collection=collection, b=b, api_key=api_key),
            timer=0
        ) 
    for t in config.tasks]

    try:
        while True:
            task_entries.sort(key=lambda k: k.timer)
        
            # sleep until the earliest task is ready
            sleep_time = task_entries[0].timer
            if sleep_time > 0:
                logger.info('sleeping %d seconds'%sleep_time)
                time.sleep(sleep_time)

            # Update task timers
            task_entries = [
                TaskEntry(
                    task=t.task,
                    timer=max(0,t.timer-sleep_time-1)) 
            for t in task_entries]

            task_entry = task_entries[0]

            assert task_entry.timer == 0

            # assume the task will be successful and stick it at the end of the line
            task_entries[0] = TaskEntry(
                task=task_entry.task, 
                timer=task_entry.timer+len(task_entries)
            )

            try:
                # if the task has work to do, do it
                if task_entry.task.next():
                    logger.info(task_entry.task.__class__.__name__)
                    task_entry.task.run()

                # otherwise stick it even further back in the line
                else:
                    logger.info('Postponing: %s'%task_entry.task.__class__.__name__)
                    task_entries[0] = TaskEntry(
                        task=task_entry.task, 
                        timer=task_entry.timer+2*len(task_entries)
                    )

            # log transient errors locally 
            except Exception, exc:
                logger.info('%s: %s'%(task_entry.task.__class__.__name__, exc))
    except KeyboardInterrupt:
        pass

    # send me an email if the script dies
    except Exception, Exc:
        text = """
            host: %s,
            pid: %d,
            error: %s
        """%(socket.gethostname(), os.getpid(), Exc)
        msg = MIMEText(text)
        me = 'blink@%s'%(socket.gethostname())
        you = config.email
        msg['Subject'] = 'blink failure'
        msg['From'] = me
        msg['To'] = you

        s = smtplib.SMTP('localhost')
        s.sendmail(me, [you], msg.as_string())
        s.quit()
 
