import sys
import requests
import json

class EsmondConnection:
    '''
        Extenable Object for storing query metadata.
        Converts "_" character in kwarg keys to "-" for url param insertion to convert from python syntax to query param.
    '''
    def __init__(self, ma_url, **kwargs):
        self.params = {}
        self.ma_url = ma_url
        for key in kwargs:
            rkey = key.replace("_", "-").replace("source", "input-source").replace("destination", "input-destination")
            self.params[rkey] = kwargs[key]
        self.query_url = ma_url + "?"
        for key in self.params:
            self.query_url = self.query_url + key + '=' + self.params[key] + '&'

    def get_metadata(self):
        data = None
        try:
            response = requests.get(self.query_url)
            data = response.json()
        except RequestException as e:
            raise AttributeError(RequestException)
        return data

    def get_data_url(self, md, event_type, summary=None):
        event = [event for event in md['event-types'] if event['event-type'] == event_type][0]
        if summary is None:
            base_uri = event['base-uri']
            return self.ma_url + base_uri
        else:
            summaries = [s for s in event['summaries'] if s['summary-window'] == str(summary)]
            return self.ma_url + summaries[0]['uri']
    
    def get_data(self, md, event_type, time_start=None, summary=None):
        '''
        Extracts the actual test data for a given query, eg. {throughput:123456, ts:98765432}
        
        param: event_type - specify the string value of the event you are looking
        for in your query result
        
        param(optional): time_start - get data starting a this timestamp
        
        returns - whatever collection the specified event in esmond conforms to.
        
        '''
        data_url = self.get_data_url(md, event_type, summary)
        data_url = (data_url + "?time-start=" + str(time_start)) if time_start else data_url
        try:
            data = requests.get(data_url)
            if data.status_code != 200:
                raise ValueError("Server response is not 200 OK!")
        except (requests.exceptions.RequestException, ValueError) as e:
            log.error("Failure getting data from {}: {}".format(data_url, e))
            return []
        return data.json()
    
if __name__ == "__main__":
    query = EsmondConnection("http://um-ps01.osris.org",
                             event_type = "throughput",
                             source = "um-ps01.osris.org",
                             time_range="86400")

