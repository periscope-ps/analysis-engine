import networkx
from networkx.algorithms.shortest_paths import single_source_shortest_path as sssp
from unisanalysis.graph import Grapher
from unis import Runtime

# Setup connection to remote database
remote_db = 'http://localhost:8888'
rt = Runtime(remote_db)

# Create Graph builder in "live" mode.
# Changes to the database will be reflected in
# the graph automatically
builder = Grapher(rt)

# Any nodes/links/ports within the database
# will be reflected in the graph at this point
# as vertices and edges

# Add vertex
# Matches networkx .add_node signature
node0 = builder.add_node('node0')
node1 = builder.add_node('node1')
node2 = builder.add_node('node2')


# Add edge
# Matches networkx .add_edge signature
#https://networkx.github.io/documentation/stable/reference/classes/multidigraph.html
builder.add_edge(node0, node1)
builder.add_edge(node1, node2)
builder.add_edge(node0, node2)

# Read/apply-function-to graph
with builder.graph() as G:
    print ("SSSP:")
    path = sssp(G, node0)
    for p in path.keys():
        print ([ x.name for x in path[p]])
    print ("0 -> 2 shortest path:")
    print ([ x.name for x in networkx.shortest_path(G, node0, node2) ])
