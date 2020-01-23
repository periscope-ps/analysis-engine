import threading, contextlib, collections

from unis.models import Node, Link, Port
from unis.services import RuntimeService, event
from networkx import MultiDiGraph

class GraphError(Exception): pass
class OperationProhibited(Exception): pass

class _Service(RuntimeService):
    def __init__(self, grapher):
        self._portmap = {}
        self._model = grapher

    @event.new_event('links')
    def add_link(self, link):
        ep = link.endpoints
        self._portmap[link] = [ep.source, ep.sink] if link.directed else [ep[0], ep[1]]
        try: self._model._add_edge(link)
        except AttributeError:
            self.runtime.log.warn("Defering attempt to graph incomplete link - {}".format(link.id))

    @event.update_event('links')
    def update_link(self, link):
        pm = self._portmap.get(link, None)
        if pm:
            ep = link.endpoints
            if not ((link.directed and pm[0] == ep.source and pm[1] == ep.sink) or \
                    (not link.directed and pm[0] == ep[0] and pm[1] == ep[1])):
                self._model._remove_edge(link, pm[0], pm[1])
                
        self._model._add_edge(link)

    @event.new_update_event('nodes')
    def add_node(self, node): self._model._add_node(node)

class Grapher(object):
    _prohibit_ops = ['add_node', 'add_nodes_from', 'remove_node', 'remove_nodes_from',
                     'add_edge', 'add_edges_from', 'add_weighted_edges_from', 'remove_edge',
                     'remove_edges_from', 'add_star', 'add_path', 'add_cycle', 'clear']
    def _prohibit(self, n):
        def _f(self, *args, **kwargs):
            raise OperationProhibited("Direct node/edge add/remove not allowed, use Grapher." + n)
        return _f
    
    def __init__(self, rt, live=True):
        self._attrs, self._live, self._rt = [], live, rt
        self._nodemap = {}
        self._port_ref = collections.defaultdict(lambda: [None, None])
        self._g = MultiDiGraph()
        for p in filter(lambda x: x in self._prohibit_ops, dir(self._g)):
            setattr(self._g, p, self._prohibit(p))

        self._lock = threading.RLock()
        if live:
            rt.addService(_Service(self))
        [c.load() for c in [rt.ports, rt.nodes, rt.links]]
        if not live:
            with self._lock:
                for n in rt.nodes: self._add_node(n)
                for l in rt.links:
                    try: self._add_edge(l)
                    except GraphError: pass

    @contextlib.contextmanager
    def graph(self):
        with self._lock:
            yield self._g

    def add_weight(self, wname:str):
        self._attrs.append(wname)
        for e in self._g.edges:
            self._g[e[0]][e[1]][e[2]][wname] = getattr(e[2], wname, None)

    def add_node(self, node, *args, **kwargs):
        if not isinstance(node, Node):
            if node in self._nodemap:
                return self._nodemap[node]
            n = self._rt.insert(Node({'name': str(node)}), commit=self._live)
            self._nodemap[node] = n
        if not self._live: self._add_node(n, *args, **kwargs)
        return n

    def remove_node(self, n:Node):
        if not isinstance(n, Node): n = self._namemap[n]
        self._rt.nodes.remove(n)
        MultiDiGraph.remove_node(self._g, n)
    
    def _add_node(self, n:Node, *args, **kwargs):
        with self._lock:
            MultiDiGraph.add_node(self._g, n, *args, **kwargs)
        for p in n.ports:
            ref = self._port_ref[p]
            ref[0] = n
            if ref[1]:
                try: self._add_edge(ref[1])
                except GraphError: pass

    def add_edge(self, u:Node, v:Node, *args, **kwargs):
        if not isinstance(u, Node): u = self._nodemap[u]
        if not isinstance(v, Node): v = self._nodemap[v]
        l = Link({**kwargs, **{'directed': kwargs.get('directed', False)}})
        p1 = self._rt.insert(Port(), commit=self._live)
        p2 = self._rt.insert(Port(), commit=self._live)
        u.ports.append(p1)
        v.ports.append(p2)
        if l.directed: l.endpoints = {'source': p1, 'sink': p2}
        else: l.endpoints = [p1, p2]
        l.extendSchema('endpoints')

        self._rt.insert(l, commit=self._live)
        if not self._live: self._add_edge(l, *args, **kwargs)
        return l

    def remove_edge(self, u:Node, v:Node, key:Link=None):
        if not isinstance(u, Node): u = self._nodemap[u]
        if not isinstance(v, Node): v = self._nodemap[v]
        if not key:
            key = [l[2] for l in self._g.edges]
        key = key if isinstance(key, list) else [key]
        for k in key:
            was_directed, ep = True, k.endpoints
            p1, p2 = (ep.source, ep.sink) if k.directed else (ep[0], ep[1])
            if not k.directed:
                was_directed = False
                k.directed = True
                k.endpoints = {'source': p2, 'sink': p2}
            self._remove_edge(k, p1, p2)

        self._rt.links.remove(key)
        if was_directed:
            self._rt.ports.remove(p1)
            self._rt.ports.remove(p2)

    def _add_edge(self, link:Link, *args, **kwargs):
        ep = link.endpoints
        if not ((link.directed and ep.source and ep.sink) or (not link.directed and ep[0] and ep[1])):
            raise GraphError("Incomplete link")

        p1, p2 = (ep.source, ep.sink) if link.directed else (ep[0], ep[1])
        pr1, pr2 = self._port_ref[p1], self._port_ref[p2]
        pr1[1] = pr2[1]= link
        
        if pr1[0] and pr2[0]:
            kwargs.update(key=link, metadata=link)
            with self._lock:
                MultiDiGraph.add_edge(self._g, pr1[0], pr2[0], source=p1, sink=p2, *args, **kwargs)
                if not link.directed:
                    MultiDiGraph.add_edge(self._g, pr2[0], pr1[0], source=p2, sink=p1, *args, **kwargs)

    def _remove_edge(self, link:Link, source:Port, sink:Port):
        pr1, pr2 = self._port_ref[source], self._port_ref[sink]

        with self._lock:
            MultiDiGraph.remove_edge(self._g, pr1[0], pr2[0], key=link)
            if not link.directed: MultiDiGraph.remove_edge(self._g, pr2[0], pr1[0], key=link)
