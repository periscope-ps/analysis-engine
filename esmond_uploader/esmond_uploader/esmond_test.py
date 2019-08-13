import sys
import json
import requests
import logging
import time
from collections import defaultdict

from unis import Runtime
from unis.models import *
from .esmond_conn import EsmondConnection
from .utils import UnisUtil
from .settings import TOOL_EVENT_TYPES, DEF_WINDOW
'''
    In this file, create different classes that handle different testing data from Esmond and
    push the data into unis.

    The base class for interacting with Esmond is EsmondTest

    Define subclasses that extend the base class for event-type specific implementation.
'''

log = logging.getLogger("esmond_test")

class ArchiveTest:
    def __init__(self, ma_url, md, upload=False):
        self.metadata = md
        self.latest = dict()
        self.data = dict()
        self.conn = EsmondConnection(ma_url)
        
    def fetch(self):
        has_data = False
        ret = defaultdict(dict)
        now = int(time.time())
        for et in self.metadata.get('event-types', []):
            et_name = et['event-type']
            window = self.latest.get(et_name, (now-DEF_WINDOW))
            self.latest[et_name] = now
            data = self.conn.get_data(self.metadata, et_name, window)
            if len(data):
                has_data = True
                ret[et_name]['base'] = data

            if et.get('summaries', None):
                for s in et['summaries']:
                    swin = s['summary-window']
                    data = self.conn.get_data(self.metadata, et_name,
                                              window, summary=swin)
                    if len(data):
                        has_data = True
                        ret[et_name][swin] = data
        return (has_data, ret)
                
class MeshEntry:
    def __init__(self, tool, src, dst, archive):
        self.src = src
        self.dst = dst
        self.tool_name = tool
        self.metadata = None
        self.eventTypes = TOOL_EVENT_TYPES.get(tool, [])
        
        # TODO: allow query of multiple archives
        self.ma_url = archive[0]['read_url']
        
        # An EsmondCOnnection object will construct an API query based on kwargs
        # after ma_url
        self.conn = EsmondConnection(self.ma_url, source=src,
                                     destination=dst, tool_name=tool)
                
    def get_metadata(self):
        log.debug("Pulling metadata from Esmond for {} / {} -> {}".format(self.tool_name,
                                                                          self.src,
                                                                          self.dst))
        self.metadata = self.conn.get_metadata()
        return self.metadata

    def get_archive(self):
        return self.ma_url

'''
Define Subclasses for individual ArchiveTest types here.

Classes defined here are serve mainly to provide an interface for grabbing test
data from Esmond. Different tests can have different result formats.  Classes
should provide the same interface of (self, archive_url, source, destination,
runtime)

'''    
class ThroughputTest(ArchiveTest):
    def fetch(self, upload=False):
        has_data = False
        ret = dict()
        for et in self.eventTypes:
            data = self._fetch(et)
            if len(data):
                has_data = True
                ret[et] = data
            if upload:
                self.upload_data(data, et)
        return (has_data, ret)

class HistogramOWDelayTest(ArchiveTest):
    def fetch(self, upload=False):
        ret = dict()
        self.upload = upload

        data = self._fetch("histogram-owdelay", summary=300)
        if len(data):
            has_data = True
            res = self.handle_histogram_owdelay(data)
            ret["histogram-owdelay"] = res
        
        data = self._fetch("packet-count-lost")
        if len(data):
            has_data = True
            res = self.handle_packet_count_loss(data)
            ret["packet-count-lost"] = res
        return (has_data, ret)

    def handle_packet_count_loss(self, data):
        if len(data) > 1 and type(data) is list:
            data = data[-1]
        elif len(data) == 1:
            data = data[0]

        if self.upload:
            try:
                self.upload_data(data, "packet-count-loss")
            except:
                log.error("Could not upload data for packet-loss-count | src %s, dst: %s", self.src,self.dst)
        return data

    def handle_histogram_owdelay(self, data):
        if len(data) > 1 and type(data) is list:
            data = data[-1]
        elif type(data) is list and len(data) == 1:
            data = data[0]
        elif not len(data):
            return data
            
        temp_total = 0
        packet_total = 0
        for k, v in data['val'].items():
            temp_total = temp_total + (float(k) * v)
            packet_total = packet_total + int(v)

        avg = temp_total / packet_total
        
        res = {"val": avg, "ts":data["ts"]}
        if self.upload:
            try:
                self._upload_data(res, "histogram-owdelay")
            except:
                log.error("Could not upload data for histogram-owdelay | src: %s, dst: %s", self.src, self.dst)
        return res

if __name__ == "__main__":
    rt = Runtime("http://iu-ps01.osris.org:8888")
    throughput = ThroughputTest("http://iu-ps01.osris.org", source="192.168.10.202", destination="192.168.10.204", runtime=rt)
    data = throughput.fetch(time_range=3600, upload=True)

    #latency    = HistogramOWDelayTest("http://iu-ps01.osris.org", source="192.168.10.202", destination="192.168.10.204", runtime=rt)
    #data       = latency.fetch(time_range=300, upload=True)
    print(data)
