#!/usr/bin/env python

import boto.ec2
import re
import ConfigParser

from fabric.api import *

def find_blink_instances():
    config = ConfigParser.ConfigParser()
    config.read('blink.cfg')

    aws_key = config.get('aws', 'aws_key')
    aws_secret = config.get('aws', 'aws_secret')

    conn = boto.ec2.connect_to_region(
        'us-east-1',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
    )
    reservations = conn.get_all_instances()

    name_matcher = re.compile('blink slave \d+')

    for reservation in reservations:
        for instance in reservation.instances:
            if 'Name' in instance.tags:
                if name_matcher.match(instance.tags['Name']) is not None:
                    yield instance

instances = list(find_blink_instances())
env.user = 'ubuntu'
env.hosts = [i.public_dns_name for i in instances]
env.key_filename = '/home/kmatzen/kmatzenvision.pem'

def hostname():
    run('hostname')

def upgrade():
    try:
        run('ls blink')
    except:
        install()
    with cd('blink'):
        run('git pull')
    configure()
    stop()
    start()

def install():
    run('git clone https://github.com/kmatzen/blink.git')
    configure()

def configure():
    put('blink.cfg', 'blink/blink.cfg')

def stop():
    run('tmux kill-session -t blink', warn_only=True)

def start():
    with cd('blink'):
        run('tmux new-session -d -s blink ./manager.py', pty=False)

def status():
    run('ps aux|grep python')
