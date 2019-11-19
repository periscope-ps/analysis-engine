import logging, sys, threading
from unis import Runtime
from unis.models import Metadata, Link, Node, Port

log = logging.getLogger("esmond_up.utils")

class UnisUtil:
    def __init__(self, rt=None):
        self.rt = rt
        
        self.rt.addService("unis.services.graph.UnisGrapher")
        self.rt.nodes.load()
        self.rt.ports.load()
        self.rt.links.load()
        self.rt.metadata.load()

    '''
        NOTE: Ideally this function should just return 2 links. But because the nodes in the TechX demo 
        are not adjacent we are returning a 3rd link, which is the switch interconnect between 'adjacent'
        nodes. This is will likely need to be revisited later.
    '''
    def get_links(self, src_ip, dst_ip):
        
        try:
            src_node = next(self.rt.nodes.where(lambda n: n.properties.mgmtaddr == src_ip))
            dst_node = next(self.rt.nodes.where(lambda n: n.properties.mgmtaddr == dst_ip))
        except:
            print("Could not find nodes. get_links( "  + src_ip + ", " + dst_ip + ")")
            return None, None

        edges = []
        for e in self.rt.graph.edges:
            valid = any(n in e for n in [src_node,dst_node])
            if valid:
                edges.append(e)
            
        print("getting links")         
        switch_names = []
        for e in edges:
            if("switch" in e[0].name and (e[0].name not in switch_names)):
                switch_names.append(e[0].name)
        print("sw names", switch_names)
        try:
            sw0 = next(self.rt.nodes.where(lambda n: n.name == switch_names[0]))
            sw1 = next(self.rt.nodes.where(lambda n: n.name == switch_names[1]))
            print(sw0.name, sw1.name)
            for e in self.rt.graph.edges:
                if e[0].name == sw0.name and e[1].name == sw1.name:
                    edges.append(e)
                    print(e[0].name, e[1].name)
                    return [e[2]]
                    break
                elif e[1].name == sw0.name and e[0].name == sw1.name:
                    
                    print(e[0].name, e[1].name)
                    edges.append(e)
                    return [e[2]]
                    break
        except:
            print("Could not find intermediate link")
            return [edges[0][2], edges[1][2]]
        
        #else:
        #    return None 

        return [edges[1][2], edges[2][2], edges[3][2]]

    def check_create_virtual_link(self, src_ip, dst_ip):
        try:
            src_port = next(self.rt.ports.where(lambda p: p.address.address == src_ip))
            dst_port = next(self.rt.ports.where(lambda p: p.address.address == dst_ip))
        except Exception as e:
            return []

        link_name = "virtual:{}:{}".format(src_port.address.address,
                                           dst_port.address.address)
        link = self.rt.links.first_where({"name": link_name})
        
        if link is None:
            print("Creating new virtual link between {}:{} and {}:{}".format(src_port.name,
                                                                             src_port.address.address,
                                                                             dst_port.name,
                                                                             dst_port.address.address))
            link = Link({"name": link_name,
                         "properties":{"type":"virtual"},
                         "directed": False,
                         "endpoints":[src_port, dst_port]})
            self.rt.insert(link, commit=True)
            return [link]

        return [link]

    def check_create_metadata(self, subject, **kwargs):
        event_type = kwargs['event']
        log.debug("looking for event type {} for subject: {}".format(event_type,subject.selfRef))
        try:
            meta = next(self.rt.metadata.where(lambda x: x.subject == subject and x.eventType == event_type and
                                               x.parameters.source == kwargs['src'] and
                                               x.parameters.destination == kwargs['dst']))
            log.debug("FOUND METADATA {}".format(meta.selfRef))
        except (StopIteration, AttributeError, Exception):
            meta = self.rt.insert(Metadata({'eventType': event_type,
                                            'subject': subject,
                                            'parameters': {'source': kwargs['src'],
                                                           'destination': kwargs['dst'],
                                                           'archive': kwargs['archive']}}),
                                  commit=True)
            log.debug("Creating metadata obj - {} ".format(meta.selfRef))
        self.rt.flush()
        return meta.data
    
    def upload_data(self, data, job, archive):
        '''
            Upload the test data to the correct metadata tag.
            - finds the link resources and their metadata objects
            - if there is no associated metadata obj for a link, creates one
            - adds the last test value to each metadata obj
        '''
        agent = job['measurement-agent']
        src_node = job['input-source']
        dst_node = job['input-destination']
        src_ip = job['source']
        dst_ip = job['destination']

        log.info("Uploading to UNIS: test data for {} -> {}".format(src_node, dst_node))

        subject_links = self.check_create_virtual_link(src_ip, dst_ip)

        for l in subject_links:
            for i in range(0, len(job['event-types'])):
                try:
                    event_type = job['event-types'][i]['event-type']
                    data_values = data[event_type]['base']
                    m = self.check_create_metadata(l, src=src_node, dst=dst_node,
                                                   archive=archive, event=event_type)
                    for j in range(len(data_values)):
                        m.append(data_values[j]["val"], ts=data_values[j]["ts"])
                except Exception as e:
                    print("Could not add data: {}".format(e))

    def jobs_to_nodes(self, jobs):
        for j in jobs:
            agent = j['measurement-agent']
            src_node = j['input-source']
            dst_node = j['input-destination']
            src_ip = j['source']
            dst_ip = j['destination']

            try:
                snode = next(self.rt.nodes.where(lambda n: n.name == src_node))
            except:
                p = Port()
                p.name = "eth0"
                p.address.type = "ipv4"
                p.address.address = src_ip
                n = Node()
                n.name = src_node
                n.ports.append(p)
                self.rt.insert(p, commit=True)
                self.rt.insert(n, commit=True)

            try:
                dnode = next(self.rt.nodes.where(lambda n: n.name == dst_node))
            except:
                p = Port()
                p.name = "eth0"
                p.address.type = "ipv4"
                p.address.address = dst_ip
                n = Node()
                n.name = dst_node
                n.ports.append(p)
                self.rt.insert(p, commit=True)
                self.rt.insert(n, commit=True)

        self.rt.flush()
    
if __name__ == "__main__":
    util = UnisUtil(rt=Runtime("http://iu-ps01.osris.org:8888"))
    links = util.check_create_virtual_link("192.168.10.202", "192.168.10.204")
    print(util.check_create_metadata(links[0], event="throughput"))
    
