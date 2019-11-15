import logging
from unis import Runtime
from unis.models import Metadata, Link

class UnisUtil:
    def __init__(self, rt=None):
        self.rt = rt
        
        self.rt.addService("unis.services.graph.UnisGrapher")
        self.rt.nodes.load()
        self.rt.ports.load()
        self.rt.links.load()

        logging.basicConfig(filename='logs/esmond_uploader.log',level=logging.DEBUG)
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
        print("Checking for virtual link between " + src_ip + " and " + dst_ip)
        try:
            src_node = next(self.rt.nodes.where(lambda n: n.properties.mgmtaddr == src_ip))
            dst_node = next(self.rt.nodes.where(lambda n: n.properties.mgmtaddr == dst_ip))
        
        except Exception as e:
            print(e)
            print("Could not find nodes. get_links( "  + src_ip + ", " + dst_ip + ")")
            return None, None
         
        print("found nodes - src: ", src_node,", dst:", dst_node)

        link_name = "virtual:" + src_node.name + ":" + dst_node.name
        link = self.rt.links.first_where({"name": link_name})
        
        if link is None:
            print("Creating new virtual link between ", src_node.name, " and ", dst_node.name)
            link = Link({"name": link_name, "properties":{"type":"virtual"}, "directed": False, "endpoints":[src_node.ports[0], dst_node.ports[0]]})
            self.rt.insert(link, commit=True)
        
        return link


    def check_create_metadata(self, subject, **kwargs):
        event_type = kwargs['event']
        print("looking for event type", event_type, "for subject :", subject.selfRef)
        try:
            meta = next(self.rt.metadata.where({"subject": subject, "eventType": event_type}))
            if meta.parameters.source == kwargs['src'] and meta.parameters.destination == kwargs['dst']: 
                print("FOUND METADATA", meta.selfRef)            
            else:
                raise Exception("Could not find metadata")
        except Exception as e:
            print("IN EXCEPTION")
            print(e)
            logging.info("Could not find metadata for - %s", subject.selfRef)
            
            meta = self.rt.insert(Metadata({"eventType": event_type, "subject": subject, "parameters": {"source":"", "destination":"", "archive":""}}), commit=True)
            print(meta)
            logging.info("Creating metadata obj - %s ", meta.selfRef)
        
        meta.parameters.source = kwargs['src']
        meta.parameters.destination = kwargs['dst']
        meta.parameters.archive = kwargs['archive']  #[0]['url']
        self.rt.flush()
        print("Returning metadata")         
        return meta.data
    
    def upload_data(self, data, job, src_ip, dst_ip, archive):
        '''
            Upload the test data to the correct metadata tag.
            - finds the link resources and their metadata objects
            - if there is no associated metadata obj for a link, creates one
            - adds the last test value to each metadata obj
        '''
        
        logging.info("Uploading to UNIS: test data for %s -> %s", src_ip, dst_ip) 

        subject_links = [self.check_create_virtual_link(src_ip, dst_ip)]
        print("Subjects:", subject_links)
        
        for l in subject_links:
            print("Trying link", l)
            try: 
                for i in range(0, len(job['event-types'])):
                    event_type = job['event-types'][i]['event-type']
                    event_type_data = data[event_type]
                    data_values = data[event_type]['base']

                    for j in range(0, len(data_values)):
                        m = self.check_create_metadata(l, src=src_ip, dst=dst_ip, archive=archive, event=event_type)
                        print("METADATA.DATA: ", m)
                        m.append(data_values[j]["val"], ts=data_values[j]["ts"])
                    
            except Exception as e:
                print(e)
                print("Could not add data")
        return 


if __name__ == "__main__":
    util = UnisUtil(rt=Runtime("http://iu-ps01.osris.org:8888"))
    links = util.check_create_virtual_link("192.168.10.202", "192.168.10.204")
    print(util.check_create_metadata(links[0], event="throughput"))
    
