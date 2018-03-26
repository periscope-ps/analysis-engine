import requests
import argparse
import time
import random
import json

from uuid import uuid4

def create_node(url):
    url = "{}/nodes".format(url)
    nid = str(uuid4())
    data = { 'id': nid }
    requests.post(url, data=json.dumps(data))
    return nid

def create_metadata(url, nid):
    url = "{}/metadata".format(url)
    mid = str(uuid4())
    data = {
        'id': mid,
        'subject': {
            'rel': 'full',
            'href': 'http://localhost:8888/nodes/{}'.format(nid)
        },
        'eventType': 'test'
    }
    requests.post(url, data=json.dumps(data))
    return mid
    
def create_event(url, mid):
    url_to = "{}/events".format(url)
    data = { "metadata_URL": "{}/metadata/{}".format(url, mid),
             "collection_size": 100000,
             "ttl": 1500000 }
    headers= { "Content-Type": "application/perfsonar+json profile=http://unis.crest.iu.edu/schema/20160630/datum#",
               "Accept": "*/*" }
    requests.post(url_to, data=json.dumps(data), headers=headers)
    
def create_data(url, mid):
    url = "{}/data/{}".format(url, mid)
    data = { 'mid': mid, 'data': [{'ts': time.time() * 1000000, 'value': random.random()}] }
    headers= { "Content-Type": "application/perfsonar+json profile=http://unis.crest.iu.edu/schema/20160630/datum#",
               "Accept": "*/*" }
    print("--Posting", url, data)
    requests.post(url, data=json.dumps(data), headers=headers)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', type=str)
    
    args = parser.parse_args()
    nid = create_node(args.url)
    mid = create_metadata(args.url, nid)
    create_event(args.url, mid)
    
    while True:
        create_data(args.url, mid)
        time.sleep(5)
