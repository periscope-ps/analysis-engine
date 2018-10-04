import sys
import json
import requests
import logging

from esmond_query import EsmondQuery, EsmondQueryHandler
from unis import Runtime
from unis.models import *
from utils import UnisUtil
'''
    In this file, create different classes that handle different testing data from Esmond and
    push the data into unis.

    The base class for interacting with Esmond is EsmondTest

    Define subclasses that extend the base class for event-type specific implementation.
'''

class EsmondTest:
    def __init__(self,
        query,  
        runtime=None):
        
        self.query          = query 
        self.query_handler  = EsmondQueryHandler(query)
        self.base_url       = self.query_handler.base_url
        self.archive_host   = query.archive_host
        
        self.util           = UnisUtil(rt=runtime)

        logging.basicConfig(filename='logs/esmond_uploader.log',level=logging.DEBUG)
        
        return
    
    def pull(self, latest=False):
        '''
            Pull method gets the archive test entries for the given query.

            param: bool latest - set latest param to True to set the working set of tests to the most recently updated one.
            returns - a list of valid archive dicts.
            If @latest is set, returns a list with a single archive dict entry.
        '''
        logging.info("pulling test entries from Esmond")

        self.archive    = self.query_handler.get() 

        if latest:
            archive, timestamp = self.get_latest()
            self.archive = [archive]
        
        return self.archive

    def get_latest(self):    
        '''
            Sets working test archive to the most recently updated test given the query results.

            Just look at the first event in each archived test and compare timestamps.
            returns - <archive entry dict>, <timestamp value>
        '''
        logging.info("Setting working test archive to latest updated test")

        latest_archive = None
        
        if len(self.archive) == 1:
            return self.archive[0], self.archive[0]['event-types'][0]['time-updated']
        elif len(self.archive) == 0:
            return None, None
        
        latest =  max(self.archive, key=lambda x:x['event-types'][0]['time-updated'])

        return latest, latest['event-types'][0]['time-updated']

    def get_data_url(self, archive, event_type, summary_window=None):     
        
        sum_archive = archive

        if summary_window is None:
            return self.archive_host + [event for event in archive['event-types'] if event['event-type'] == event_type][0]['base-uri']
        else:
            test = [event for event in sum_archive['event-types'] if event['event-type'] == event_type][0]  
            summary = [summary for summary in test['summaries'] if summary['summary-window'] == str(summary_window)]
            return self.archive_host + summary[0]['uri']
        
    def fetch_data(self, event_type, time_range=None, summary=None):    
        '''
            Extracts the actual test data for a given query, eg. {throughput:123456, ts:98765432}
            param: event_type - specify the string value of the event you are looking for in your query result
            param(optional): time_range - limit the query only results in the given time range (recommended, mostly to avoid pulling in huge data objects)

            returns - whatever dict the specified event in esmond conforms to.
        '''
        logging.info("Begin fetching %s test data within time range %s", event_type, time_range)

        self.pull(latest=True)
        data_url = self.get_data_url(self.archive[0], event_type, summary_window=summary) 
        data_url = (data_url + "?time-range=" + str(time_range)) if time_range is not None else data_url

        try:
            data = requests.get(data_url).json()
        except requests.exceptions.RequestException as e:
            print("Failure getting data from URL: ", data_url)
            print(e)
        
        return data

    def upload_data(self, data, src_ip, dst_ip, event_type):
        '''
            Upload the test data to the correct metadata tag.
            - finds the link resources and their metadata objects
            - if there is no associated metadata obj for a link, creates one
            - adds the last test value to each metadata obj
        '''
        
        logging.info("Uploading to UNIS: %s test data for %s -> %s", event_type, src_ip, dst_ip) 

        try:
            subject_links = self.util.get_links(src_ip, dst_ip)
        except:
            print("No links")
            return None 
        
        for l in subject_links:
            print("Trying link", l)
            try: 
                m = self.util.check_create_metadata(l, event=event_type)
                m.append(data["val"], ts=data["ts"])
            except:
                print("Could not add data")
        return 


'''

       Define Subclasses for individual test types here.
       
       Classes defined here are serve mainly to provide an interface for grabbing test data from Esmond. Different tests can have different result formats.
       Classes should provide the same interface of (self, archive_url, source, destination, runtime)
'''
class ThroughputTest(EsmondTest):
    def __init__(self, archive_url, source, destination, runtime=None):
        
        self.src = source
        self.dst = destination

        query = EsmondQuery(archive_url, event_type="throughput", source=source, destination=destination)
        EsmondTest.__init__(self, query, runtime=runtime)
        
        return

    def fetch(self, time_range=None, upload=False): 
        data = self.fetch_data("throughput", time_range=time_range)
        
        if len(self.archive) == 0:
            print("No tests found for query")
            return 

        if upload:
            try:
                self.upload_data(data[-1], self.src, self.dst, event_type="throughput")
            except: 
                logging.info("Could not upload data for throughput | src: %s, dst: %s")

        return data

class HistogramOWDelayTest(EsmondTest):
    def __init__(self, archive_url, source, destination, runtime=None, summary=300):
        self.src = source
        self.dest = destination
        
        query = EsmondQuery(archive_url, event_type="histogram-owdelay", source=source, destination=destination)
        EsmondTest.__init__(self, query, runtime=runtime)
    
    def fetch(self, time_range=None, upload=False):
        data = self.fetch_data("histogram-owdelay", summary=300, time_range=time_range)
        #print(data)        
        if len(data) > 1 and type(data) is list:
            data = data[-1]
        elif type(data) is list and len(data) == 1:
            data = data[0]
        else:
            data = data
        
        
        if len(self.archive) == 0:
            print("No tests found for query")
            return
        
        temp_total = 0
        packet_total = 0
        for k, v in data['val'].items():
            temp_total = temp_total + (float(k) * v)
            packet_total = packet_total + int(v)

        avg = temp_total / packet_total
        
        res = {"val": avg, "ts":data["ts"]}
        if upload:
            try:
                self.upload_data(res, self.src, self.dest, event_type="histogram-owdelay")
            except:
                logging.info("Could not upload data for histogram-owdelay | src: %s, dst: %s", self.src, self.dest)
        return res

if __name__ == "__main__":
    rt = Runtime("http://localhost:8888")
    throughput = ThroughputTest("http://iu-ps01.osris.org", source="192.168.10.202", destination="192.168.10.204", runtime=rt)
    data = throughput.fetch(time_range=3600, upload=True)

    latency    = HistogramOWDelayTest("http://iu-ps01.osris.org", source="192.168.10.202", destination="192.168.10.204", runtime=rt)
    data       = latency.fetch(time_range=300, upload=True)
    print(data)
