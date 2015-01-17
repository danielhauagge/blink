#!/usr/bin/env python

import time
import boto.ec2
import re
import sys
import os
import logging
import socket

from common import load_config, get_aws_public_hostname, init_logger
init_logger()

from fabric.api import *

# http://examples.oreilly.com/0636920020202/ec2_launch_instance.py

def connect():
    config = load_config() #ConfigParser.ConfigParser()

    aws_key = config.get('aws', 'aws_key')
    aws_secret = config.get('aws', 'aws_secret')

    conn = boto.ec2.connect_to_region(
        'us-east-1',
        aws_access_key_id = aws_key,
        aws_secret_access_key = aws_secret,
    )

    return conn

def find_blink_instances():
    conn = connect()

    reservations = conn.get_all_instances()

    name_matcher = re.compile('blink slave \d+')

    for reservation in reservations:
        for instance in reservation.instances:
            if instance.state != 'running':
                continue
            if 'Name' in instance.tags:
                if name_matcher.match(instance.tags['Name']) is not None:
                    logging.info('%-30s %-30s', instance.tags['Name'], instance.public_dns_name)
                    yield instance


instances = list(find_blink_instances())
env.user = 'ubuntu'
env.hosts = [i.public_dns_name for i in instances]
env.key_filename = os.path.expanduser(load_config().get('ssh','identity_file'))

@task
def hostname():
    run('curl http://169.254.169.254/latest/meta-data/public-hostname')

@task
def upgrade(collection, max_images = 0):
    install()
    with cd('blink'):
        run('git pull')
    stop()
    start(collection, max_images)

@task
def install():
    config = load_config()
    try:
        run('ls blink')
    except:
        run('git clone ' + config.get('blink', 'repository'))
    configure()

@task
def configure():
    put('~/.blink', '~/.blink')
    put('~/.bashrc', '~/.bashrc')

@task
def stop():
    run('tmux kill-session -t blink', warn_only=True)

@task
def start(collection, max_images = 0):
    with cd('blink'):
        run('tmux new-session -d -s blink "./fetch.py --db-hostname {db_hostname} --collection {collection} --max-images {max_images}"'.format(db_hostname = get_aws_public_hostname(), collection = collection, max_images = max_images), pty=False)
        # run('tmux new-session -d -s blink echo', pty=False)

@task
def status():
    run('echo `ps aux | grep python | grep -v grep`')

def get_existing_slave_ids():
    existing = set()

    name_matcher = re.compile('blink slave (\d+)')
    for instance in instances:
        name = instance.tags['Name']
        groups = name_matcher.match(name).groups()
        num = int(groups[0])
        existing.add(num)
   
    return existing

def create_spot_instances():
    reservation = conn.request_spot_instances(
        spot_price,
        ami,
        count=count,
        key_name=key_name,
        instance_type=instance_type,
        #availability_zone_group=availability_zone_group,
        #placement = placement,
        security_groups=[security_group]
    )

    spot_ids = [s.id for s in reservation]

    while True:
        ready = True

        try:
            for r in conn.get_all_spot_instance_requests(spot_ids):
                print('Code: %s'%r.status.code)
                print('Update time: %s'%r.status.update_time)
                print('Message: %s'%r.status.message)
                if r.status.code != 'fulfilled':
                    ready = False

            if ready:
                break
        except:
            pass

        time.sleep(1)

    existing = get_existing_slave_ids()

    while True:
        ready = True

        for r in conn.get_all_spot_instance_requests(spot_ids):
            instance_id = r.instance_id
            reservations = conn.get_all_instances(instance_id)
            for reservation in reservations:
                for instance in reservation.instances:
                    print('State: %s'%instance.state)
                    print('Status check: %s'%(instance.system_status.status))
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

def instance_is_ssh_reachable(hostname):
    if len(hostname.strip()) == 0: return False

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    is_reachable = False
    try:
        s.connect((hostname, 22))
        is_reachable = True
    except socket.error as e:
        pass
    s.close()

    return is_reachable

def create_ondemand_instances(conn, ami, security_group, instance_type, count, key_name):
    reservation = conn.run_instances(
        ami,
        min_count=count, max_count=count,
        key_name=key_name,
        instance_type=instance_type,
        #availability_zone_group=availability_zone_group,
        #placement = placement,
        security_groups=[security_group]
    )

    instance_ids = [s.id for s in reservation.instances]

    while True:
        ready = True

        logging.info('')
        logging.info('Checking to see if all instances are in running state')

        reservations = conn.get_all_instances(instance_ids)
        for reservation in reservations:
            for reservation in reservations:
                for instance in reservation.instances:

                    if instance.state != 'running':
                        ready = False

                    if instance_is_ssh_reachable(instance.public_dns_name):
                        ssh_reachable = True
                    else:
                        ssh_reachable = False
                        ready = False

                    dns_name = instance.public_dns_name if len(instance.public_dns_name) > 0 else 'NO_DNS_NAME_YET'

                    logging.info('%-40s, %-20s, SSH=%s', dns_name , instance.state, 'YES' if ssh_reachable else 'NO')

        if ready: break

        time.sleep(1)

    logging.info('All instances up and running!')

    existing = get_existing_slave_ids()
    if len(existing) > 0:
        starting_no = max(get_existing_slave_ids()) + 1
    else:
        starting_no = 0

    logging.info('Renaming instances')
    for instance in reservation.instances:
        new_name = 'blink slave %d'%(starting_no)
        instance.add_tag('Name', new_name)
        starting_no += 1
        logging.info('Created %s', new_name)

@task
@hosts('localhost')
def terminate():
    logging.warn('Will terminate all slave instances now')

    instance_ids = [i.id for i in instances]

    conn = connect()
    conn.terminate_instances(instance_ids)

@task
@hosts('localhost')
def state():
    conn = connect()
    reservations = conn.get_all_instances()
    name_matcher = re.compile('blink slave \d+')

    for reservation in reservations:

        for instance in reservation.instances:
            if ('Name' not in instance.tags) or (name_matcher.match(instance.tags['Name']) is None): continue
            logging.info('%s: %s',  instance.tags['Name'], instance.state)

@task
@hosts('localhost')
def add_instance(count):
    conn = connect()
    config = load_config()

    ami = config.get('aws', 'ami')
    spot_price = config.getfloat('aws', 'spot_price')
    key_name = config.get('aws', 'key_name')
    instance_type = config.get('aws', 'instance_type')
    availability_zone_group = config.get('aws', 'availability_zone_group')
    #placement = config.get('aws', 'placement')
    security_group = config.get('aws', 'security_group')

    create_ondemand_instances(conn, ami, security_group, instance_type, count, key_name)
