import requests, time, unis

from unis.models import Metadata
from unis.services.data import DataService

rt_community = 'SC19'
sflow_host = "http://slate.open.sice.indiana.edu:8008"
activeflows = "/activeflows/{agent}/dl/json"

ip_map = {
    "149.165.232.118": "switch:183512110071119:vlan924", #osd03.crest.iu.edu
    "149.165.232.117": "switch:69220935633225:vlan924",  #osd02.crest.iu.edu
    "149.165.232.116": "switch:258154717813568:vlan924"  #osd01.crest.iu.edu
}

def main(args):
    rt = unis.from_community(rt_community)
    rt.addService(DataService())

    while True:
        for agent, port_name in ip_map.items():
            if not isinstance(port_name, str): continue
            port = rt.ports.first_where({'name': port_name})
            if not port:
                print("Failed lookup on port -", port_name)
                continue
            ip_map[agent] = links = []
            for l in rt.links:
                ep = l.endpoints
                if (not l.directed and port in ep) or (l.directed and (port == ep.source or port == ep.sink)):
                    links.append(l)
            if not ip_map[agent]:
                raise TypeError("Could not find link for {}".format(port.name))
            for i,link in enumerate(links):
                ip_map[agent][i] = rt.metadata.first_where({'subject': link, 'eventType': 'throughput'}) or rt.insert(Metadata({'subject': link, 'eventType': 'throughput'}), commit=True)
        if not any([isinstance(p, str) for p in ip_map.values()]): break

    rt.flush()

    while True:
        for agent, mds in ip_map.items():
            resp = requests.get(sflow_host + activeflows.format(agent=agent)).json()
            for md in mds:
                val = sum([float(v['value']) for v in resp])
                md.data.append(val)
            print("Updating throughput on", agent, "to", val, "[{}]".format(md.subject.name))

        rt.flush()
        time.sleep(3)

if __name__ == "__main__":
    main(None)
