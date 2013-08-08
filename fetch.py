#!/usr/bin/env python

from boto.s3.connection import S3Connection
import pymongo

import logging
import time
from email.mime.text import MIMEText
import os
import socket

from common import *

def build_task(task):
    print('Importing %s'%task)
    module = __import__(task)
    return getattr(module, task)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    config = load_config()

    client = pymongo.MongoClient(config.host, config.port)
    collection = client[config.database][config.collection]

    s3conn = S3Connection(config.aws_key, config.aws_secret)
    b = s3conn.get_bucket(config.bucket)
    api_key = config.api_key

    tasks = [(build_task(t),0) for t in config.tasks]

    try:
        while True:
            tasks = [(t, max(0,c-1)) for t,c in tasks]
            tasks.sort(key=lambda k: k[1])
            task = tasks[0]
            tasks[0] = (task[0], task[1]+len(tasks))
            try:
                if not task[0](collection=collection, b=b, api_key=api_key):
                    tasks[0] = (task[0], task[1]+4*len(tasks)) 
                
            except Exception, exc:
                logging.info(exc)
    except KeyboardInterrupt:
        pass
    except Exception, Exc:
        text = """
            host: %s,
            pid: %d,
            error: %s
        """%(socket.gethostname(), os.getpid(), Exc)
        msg = MIMEText(text)
        me = 'blink@%s'%(socket.gethostname())
        you = 'kmatzen@gmail.com'
        msg['Subject'] = 'blink failure'
        msg['From'] = me
        msg['To'] = you

        s = smtplib.SMTP('localhost')
        s.sendmail(me, [you], msg.as_string())
        s.quit()
 
