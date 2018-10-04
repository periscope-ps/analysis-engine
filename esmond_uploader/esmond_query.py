import sys
import requests
import json

class EsmondQuery:
    '''
        Extenable Object for storing query metadata.
    
        Converts "_" character in kwarg keys to "-" for url param insertion to convert from python syntax to query param.
    '''
    def __init__(self, archive_host, **kwargs):
        
        self.params = {}
        self.archive_host = archive_host

        for key in kwargs: 
            self.params[key.replace("_","-")] = kwargs[key]  
        
        return

class EsmondQueryHandler:
    '''
       Takes an EsmondQuery. Used for getting esmond testing data and pushing to unis.
    '''
    def __init__(self, query):
 
        self.query = query
        self.base_url = query.archive_host + "/esmond/perfsonar/archive/?"
        self.query_url = self.base_url

        for key in self.query.params:
            self.query_url = self.query_url + '&' + key + '=' + self.query.params[key]
        
        return

    def get(self):
        
        try:
            response = requests.get(self.query_url)
            self.data     = response.json()
        
        except RequestException as e:
            raise AttributeError(RequestException)
        
        return self.data
                

if __name__ == "__main__":
    query = EsmondQuery("http://um-ps01.osris.org", event_type = "throughput", source = "um-ps01.osris.org", time_range="86400")
    test  = EsmondQueryHandler(query) 

