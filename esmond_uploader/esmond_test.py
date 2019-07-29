import sys
import json
import requests
import logging
import time

from esmond_conn import EsmondConnection
from unis import Runtime
from unis.models import *
from utils import UnisUtil
from settings import TOOL_EVENT_TYPES, DEF_WINDOW
'''
    In this file, create different classes that handle different testing data from Esmond and
    push the data into unis.

    The base class for interacting with Esmond is EsmondTest

    Define subclasses that extend the base class for event-type specific implementation.
'''

class EsmondTest:
    def __init__(self, name, tool, src, dst, archive, runtime=None):
        self.name = name
        self.src = src
        self.dst = dst
        self.tool_name = tool
        self.latest = dict()
        self.metadata = None
        self.eventTypes = TOOL_EVENT_TYPES.get(tool, [])
        
        # TODO: allow query of multiple archives
        self.ma_url = archive[0]['read_url']
        
        # An EsmondCOnnection object will construct an API query based on kwargs after ma_url
        self.conn = EsmondConnection(self.ma_url, source=src, destination=dst, tool_name=tool)
        self._update_md()
        
        self.util = UnisUtil(rt=runtime)
        runtime.addService("unis.services.data.DataService")
        logging.basicConfig(filename='logs/esmond_uploader.log',level=logging.DEBUG)        
        
    def _update_md(self, latest=False):
        logging.info("Pulling metadata from Esmond")
        self.metadata = self.conn.get_metadata()

    def fetch(self, upload=False):
        pass
        
    def _fetch(self, et, summary=None):
        ret = []
        for md in self.metadata:
            now = int(time.time())
            window = self.latest.get(et, (now-DEF_WINDOW))
            self.latest[et] = now
            data = self._get_data(md, et, window, summary)
            ret = ret + data
        return ret
        
    def _get_data_url(self, md, event_type, summary=None):
        event = [event for event in md['event-types'] if event['event-type'] == event_type][0]
        if summary is None:
            '''
            for event in archive['event-types']:
                pprint.pprint(event)
                if event['event-type'] == event_type:
                    print("FOUND")
                    pprint.pprint( event)
            '''
            base_uri = event['base-uri']
            return self.ma_url + base_uri
        else:
            summaries = [s for s in event['summaries'] if s['summary-window'] == str(summary)]
            return self.ma_url + summaries[0]['uri']
        
    def _get_data(self, md, event_type, time_start=None, summary=None):
        '''
        Extracts the actual test data for a given query, eg. {throughput:123456, ts:98765432}
        
        param: event_type - specify the string value of the event you are looking
        for in your query result

        param(optional): time_start - get data starting a this timestamp
        
        returns - whatever collection the specified event in esmond conforms to.

        '''
        logging.info("Begin fetching {} test data from time {}".format(event_type, time_start))
        data_url = self._get_data_url(md, event_type, summary)
        data_url = (data_url + "?time-start=" + str(time_start)) if time_start else data_url
        try:
            data = requests.get(data_url)
            if data.status_code != 200:
                raise ValueError("Server response is not 200 OK!")
        except (requests.exceptions.RequestException, ValueError) as e:
            print("Failure getting data from {}: {}".format(data_url, e))
            return []
        return data.json()

    def _upload_data(self, data, event_type):
        '''
        Upload the test data to the correct metadata tag.
        - finds the link resources and their metadata objects
        - if there is no associated metadata obj for a link, creates one
        - adds the last test value to each metadata obj
        '''
        
        logging.info("Uploading to UNIS: {} test data for {} -> {}".format(event_type, self.src, self.dst))
        
        subject_links = [self.util.check_create_virtual_link(self.src, self.dst)]
        print("Subjects:", subject_links)
        
        for l in subject_links:
            print("Trying link", l)
            try: 
                m = self.util.check_create_metadata(l, src=self.src, dst=self.dst,
                                                    event=event_type)
                print("METADATA.DATA: ", m)
                m.append(data["val"], ts=data["ts"])
            except Exception as e:
                print(e)
                print("Could not add data")

'''
Define Subclasses for individual test types here.

Classes defined here are serve mainly to provide an interface for grabbing test
data from Esmond. Different tests can have different result formats.  Classes
should provide the same interface of (self, archive_url, source, destination,
runtime)

'''
class ThroughputTest(EsmondTest):
    def fetch(self, upload=False):
        ret = dict()
        for et in self.eventTypes:
            data = self._fetch(et)
            ret[et] = data
            if upload:
                self.upload_data(data, et)
        return ret

class HistogramOWDelayTest(EsmondTest):
    def fetch(self, upload=False):
        ret = dict()
        self.upload = upload

        data = self._fetch("histogram-owdelay", summary=300)
        res = self.handle_histogram_owdelay(data)
        ret["histogram-owdelay"] = res
        
        data = self._fetch("packet-count-lost")
        res = self.handle_packet_count_loss(data)
        ret["packet-count-lost"] = res
        return ret

    def handle_packet_count_loss(self, data):
        if len(data) > 1 and type(data) is list:
            data = data[-1]
        elif len(data) == 1:
            data = data[0]

        if self.upload:
            try:
                self.upload_data(data, "packet-count-loss")
            except:
                logging.info("Could not upload data for packet-loss-count | src %s, dst: %s", self.src,self.dst)
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
                logging.info("Could not upload data for histogram-owdelay | src: %s, dst: %s", self.src, self.dst)
        return res

if __name__ == "__main__":
    rt = Runtime("http://iu-ps01.osris.org:8888")
    throughput = ThroughputTest("http://iu-ps01.osris.org", source="192.168.10.202", destination="192.168.10.204", runtime=rt)
    data = throughput.fetch(time_range=3600, upload=True)

    #latency    = HistogramOWDelayTest("http://iu-ps01.osris.org", source="192.168.10.202", destination="192.168.10.204", runtime=rt)
    #data       = latency.fetch(time_range=300, upload=True)
    print(data)
