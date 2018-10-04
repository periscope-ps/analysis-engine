import logging
from unis import Runtime
from unis.models import Metadata

class UnisUtil:
    def __init__(self, rt=None):
        self.rt = rt
        self.rt.addService("unis.services.data.DataService")
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
            print("Could not find nodes. get_links(",src_ip,",",dst_ip,")")
            return None, None

        edges = []
        for e in self.rt.graph.edges:
            valid = any(n in e for n in [src_node,dst_node])
            if valid:
                edges.append(e) 
        
        # Get the switch link, huge assumption, needs revisiting later after techX
        if len(edges) == 2:
            try:
                sw0 = next(self.rt.nodes.where(lambda n: n.name == edges[0][1].name))
                sw1 = next(self.rt.nodes.where(lambda n: n.name == edges[1][1].name))

                for e in self.rt.graph.edges:
                    if e[0].name == sw0.name and e[1].name == sw1.name:
                        edges.append(e)
                        break
                    elif e[1].name == sw0.name and e[0].name == sw1.name:
                        edges.append(e)
                        break
            except:
                print("Could not find intermediate link")
                return [edges[0][2], edges[1][2]]
        
        else:
            return None

        return [edges[0][2], edges[1][2], edges[2][2]]

    def check_create_metadata(self, subject, **kwargs):
        
        event_type = kwargs['event']
        print("looking for event type", event_type, "for subject :", subject.selfRef)
        try:
            meta = next(self.rt.metadata.where({"eventType":event_type, "subject": subject}))
            print("FOUND METADATA", meta.selfRef)            
        except:
            print("IN EXCEPTION")
            logging.info("Could not find metadata for - %s", subject.selfRef)
            
            meta = self.rt.insert(Metadata({"eventType": event_type, "subject": subject}), commit=True)
            print(meta)
            logging.info("Creating metadata obj - %s ", meta.selfRef)
        
        self.rt.flush()
        print("Returning metadata")         
        return meta.data


if __name__ == "__main__":
    util = UnisUtil(rt=Runtime("http://localhost:8888"))
    links = util.get_links("192.168.10.202", "192.168.10.204")
    print(util.check_create_metadata(links[0], event="throughput"))
    
