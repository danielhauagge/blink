#!/usr/bin/env python

import time
import subprocess
import multiprocessing
import atexit

def terminate():
    global procs
    for proc in procs:
        try:
            proc.kill()
        except:
            pass

if __name__ == '__main__':
    args = ['./fetch.py']

    procs = [subprocess.Popen(args) for i in xrange(100*multiprocessing.cpu_count())]

    atexit.register(terminate)

    def proc_generator(procs):
        for proc in procs:
            if proc.poll() is not None:
                yield subprocess.Popen(args)
            else:
                yield proc

    while True:
        procs = list(proc_generator(procs))
        time.sleep(1)
