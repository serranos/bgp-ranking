#!/usr/bin/python
# -*- coding: utf-8 -*-
# Inspired by : http://gitorious.org/forban/forban/blobs/master/bin/forbanctl

"""
Start the service fetching the dumps of routing information (bview files)
provided by RIPE NCC
"""
import os
import sys
import ConfigParser

import signal

def usage():
    print "start_fetch_bview.py (start|stop)"
    exit (1)

if __name__ == '__main__':
    config = ConfigParser.RawConfigParser()
    config_file = "/path/to/bgp-ranking.conf"
    config.read(config_file)
    root_dir = config.get('directories','root')
    sys.path.append(os.path.join(root_dir,config.get('directories','libraries')))
    from helpers.initscript import *
    services_dir = os.path.join(root_dir,config.get('directories','services'))

    service = os.path.join(services_dir, "fetch_bview")

    syslog.openlog('BGP_Ranking_Bview', syslog.LOG_PID, syslog.LOG_LOCAL5)

    if len(sys.argv) < 2:
        usage()

    if sys.argv[1] == "start":
        print('Start fetching of bview')
        syslog.syslog(syslog.LOG_INFO, 'Start fetching of bview')
        proc = service_start_once(servicename = service, processname = service)
    elif sys.argv[1] == "stop":
        print('Stop fetching of bview')
        syslog.syslog(syslog.LOG_INFO, 'Stop fetching of bview')
        pid = pidof(processname=service)
        if pid:
            pid = pid[0]
            try:
                os.kill(int(pid), signal.SIGKILL)
            except OSError, e:
                print("bview fetching unsuccessfully stopped")
                syslog.syslog(syslog.LOG_ERR,"bview fetching unsuccessfully stopped")
            rmpid(processname=service)
        else:
            print('No running bview fetching processes')
            syslog.syslog(syslog.LOG_INFO, 'No running bview fetching processes')
    else:
        usage()
