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

if __name__ == "__main__":
    query = EsmondConnection("http://um-ps01.osris.org",
                             event_type = "throughput",
                             source = "um-ps01.osris.org",
                             time_range="86400")

