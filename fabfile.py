#!/usr/bin/env python

import time
import boto.ec2
import re
import ConfigParser

from fabric.api import *

def connect():
    config = ConfigParser.ConfigParser()
    config.read('blink.cfg')

    aws_key = config.get('aws', 'aws_key')
    aws_secret = config.get('aws', 'aws_secret')

    conn = boto.ec2.connect_to_region(
        'us-east-1',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
    )

    return conn

def find_blink_instances():
    conn = connect()

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

@task
def hostname():
    run('hostname')

@task
def upgrade():
    install()
    with cd('blink'):
        run('git pull')
    stop()
    start()

@task
def install():
    try:
        run('ls blink')
    except:
        run('git clone https://github.com/kmatzen/blink.git')
    configure()

@task
def configure():
    put('blink.cfg', 'blink/blink.cfg')

@task
def stop():
    run('tmux kill-session -t blink', warn_only=True)

@task
def start():
    with cd('blink'):
        run('tmux new-session -d -s blink ./manager.py', pty=False)

@task
def status():
    run('ps aux|grep python')

@task
@hosts('localhost')
def add_instance():
    conn = connect()
    reservation = conn.request_spot_instances(0.06, 'ami-42a6db2b', key_name='kmatzenvision', instance_type='m3.xlarge', availability_zone_group='us-east-1d', security_groups=['kmatzen'])
   
    spot_ids = [s.id for s in reservation]
 
    while True:
        ready = True
   
        for r in conn.get_all_spot_instance_requests(spot_ids):
            print('Code: %s'%r.status.code)
            print('Update time: %s'%r.status.update_time)
            print('Message: %s'%r.status.message)
            if r.status.code != 'fulfilled':
                ready = False

        if ready:
            break

        time.sleep(1)

    existing = set()

    name_matcher = re.compile('blink slave (\d+)')
    for instance in instances:
        name = instance.tags['Name']
        groups = name_matcher.match(name).groups()
        num = int(groups[0])
        existing.add(num)

    while True:
        ready = True

        for r in conn.get_all_spot_instance_requests(spot_ids):
            instance_id = r.instance_id
            reservations = conn.get_all_instances(instance_id)
            for reservation in reservations:
                for instance in reservation.instances:
                    print('State: %s'%instance.state)
                    if instance.state != 'running':
                        ready = False

        if ready:
            break

        time.sleep(1)

    for r in conn.get_all_spot_instance_requests(spot_ids):
        instance_id = r.instance_id
        reservations = conn.get_all_instances(instance_id)
        for reservation in reservations:
            for instance in reservation.instances:
                for num in xrange(len(existing)+1):
                    if num not in existing:
                        new_name = 'blink slave %d'%num
                        existing.add(num)
                        break

                instance.add_tag('Name', new_name)
                print('New node named %s'%new_name)
