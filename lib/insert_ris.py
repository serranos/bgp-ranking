# -*- coding: utf-8 -*-
"""
    bgp_ranking.lib.InsertRIS
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Insert the RIS Whois information in the database.

"""

import re

import redis
import time
import os
import sys
import ConfigParser

from whois_parser.whois_parsers import *

import syslog
import datetime

import dateutil.parser

class InsertRIS(object):
    """
        Link the entries with their ASN.

        A new asn "object" is created by :meth:`add_asn_entry` if it does not already exists
    """
    default_asn_desc = None
    max_consecutive_errors = 5

    def __init__(self):
        syslog.openlog('BGP_Ranking_Fetching_RIS', syslog.LOG_PID, syslog.LOG_LOCAL5)

        self.config = ConfigParser.RawConfigParser()
        config_file = "/path/to/bgp-ranking.conf"
        self.config.read(config_file)
        self.separator = self.config.get('input_keys','separator')

        self.default_asn = self.config.get('modules_global','default_asn')

        self.key_asn = self.config.get('input_keys','asn')
        self.key_owner = self.config.get('input_keys','owner')
        self.key_ips_block = self.config.get('input_keys','ips_block')
        self.cache_db   = redis.Redis(port = int(self.config.get('redis','port_cache')),\
                                        db = int(self.config.get('redis','cache_ris')))
        self.cache_db_0 = redis.Redis(port = int(self.config.get('redis','port_cache')) ,\
                                        db = int(self.config.get('redis','temp')))
        self.global_db  = redis.Redis(port = int(self.config.get('redis','port_master')),\
                                        db = int(self.config.get('redis','global')))
        default_asn_members = self.global_db.smembers(self.config.get('modules_global','default_asn'))
        if len(default_asn_members) == 0 :
            self.default_asn_key = self.add_asn_entry(\
                                    self.config.get('modules_global','default_asn'), \
                                    self.config.get('modules_global','default_asn_descr'), \
                                    self.config.get('modules_global','default_asn_route'))
        else:
            self.default_asn_key = '{asn}{sep}{tstamp}'.format(asn=self.config.get('modules_global','default_asn'), sep = self.separator, tstamp=default_asn_members.pop())

    def add_asn_entry(self, asn, owner, ips_block):
        """
            Add a new subnet to the ASNs known by the system,
            only if the subnet is not already present. Elsewhere, simply return
            the value from the database.
        """
        key = None
        asn_timestamps = self.global_db.smembers(asn)
        key_list = []
        for asn_timestamp in asn_timestamps:
            temp_key = "{asn}{sep}{timestamp}".format(asn=asn, sep = self.separator, timestamp=asn_timestamp)
            key_list.append("{key}{sep}{ips_block}".format(key = temp_key, sep = self.separator, ips_block = self.key_ips_block))
        ips_blocks = []
        if len(key_list) != 0:
            ips_blocks = self.global_db.mget(key_list)
        i = 0
        for block in ips_blocks:
            if block == ips_block:
                asn, timestamp, b = key_list[i].split(self.separator)
                temp_key = "{asn}{sep}{timestamp}".format(asn=asn, sep = self.separator, timestamp=timestamp)
                if self.global_db.get("{key}{sep}{owner}".format(key = temp_key,\
                    sep = self.separator, owner = self.key_owner)) == owner:
                    key = temp_key
                    break
            i +=1
        if key is None:
            timestamp = datetime.datetime.utcnow().isoformat()
            key = "{asn}{sep}{timestamp}".format(asn=asn, sep = self.separator, timestamp=timestamp)
            to_set = {  "{key}{sep}{owner}"     .format(key = key, sep = self.separator, owner = self.key_owner)        : owner,
                        "{key}{sep}{ips_block}" .format(key = key, sep = self.separator, ips_block = self.key_ips_block): ips_block}
            pipeline = self.global_db.pipeline(False)
            pipeline.sadd(asn, timestamp)
            pipeline.mset(to_set)
            pipeline.execute()
        return key

    def update_db_ris(self, data):
        """
            Use :meth:`add_asn_entry` to update the database with the RIS whois informations
            from :class:`WhoisFetcher` and return the corresponding entry.
        """
        splitted = data.partition('\n')
        ris_origin = splitted[0]
        riswhois = splitted[2]
        ris_whois = Whois(riswhois,  ris_origin)
        if not ris_whois.origin:
            return self.default_asn_key
        else:
            asn_key = self.add_asn_entry(ris_whois.origin, ris_whois.description, ris_whois.route)
            return asn_key

    def get_ris(self):
        """
            Get the RIS whois information if the IPs without ASNs and put it into redis.
            The entry has now a link with his ASN.
        """
        key_no_asn = self.config.get('redis','no_asn')
        errors = 0
        to_return = False
        while True:
            sets = self.cache_db_0.smembers(key_no_asn)
            if len(sets) == 0:
                break
            to_return = True
            for ip_set in sets:
                errors = 0
                ip_set_card = self.cache_db_0.scard(ip_set)
                if ip_set_card == 0:
                    self.cache_db_0.srem(key_no_asn, ip_set)
                    continue
                for i in range(ip_set_card):
                    temp, date, source, key = ip_set.split(self.separator)
                    ip_details = self.cache_db_0.spop(ip_set)
                    if ip_details is None:
                        break
                    ip, timestamp = ip_details.split(self.separator)
                    entry = self.cache_db.get(ip)
                    if entry is None:
                        errors += 1
                        self.cache_db_0.sadd(ip_set, ip_details)
                        if errors >= self.max_consecutive_errors:
                            self.cache_db_0.sadd(self.config.get('redis','key_temp_ris'), ip)
                    else:
                        errors = 0
                        asn = self.update_db_ris(entry)
                        date = dateutil.parser.parse(timestamp).date().isoformat()
                        index_day_asns_details = '{date}{sep}{source}{sep}{key}'.format(sep = self.separator, \
                                                        date=date, source=source, \
                                                        key=self.config.get('input_keys','index_asns_details'))
                        index_day_asns = '{date}{sep}{source}{sep}{key}'.format(sep = self.separator, \
                                                        date=date, source=source, \
                                                        key=self.config.get('input_keys','index_asns'))
                        index_as_ips = '{asn}{sep}{date}{sep}{source}'.format(sep = self.separator, asn = asn,\
                                                        date=date, source=source)
                        if self.global_db.sismember(index_as_ips, ip_details) is False:
                            self.global_db.sadd(index_day_asns_details, asn)
                            self.global_db.sadd(index_day_asns, asn.split(self.separator)[0])
                            self.global_db.sadd(index_as_ips, ip_details)
                            to_return = True
                    if i%100000 == 0:
                        syslog.syslog(syslog.LOG_INFO, str(self.cache_db_0.scard(ip_set)) + ' RIS Whois to insert on ' + ip_set)
            time.sleep(int(self.config.get('sleep_timers','short')))
        return to_return
