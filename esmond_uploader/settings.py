from prometheus_client.core import GaugeMetricFamily, HistogramMetricFamily


DEF_INTERVAL=120
DEF_WINDOW=600

MESH_TO_PSTOOL = {
    "perfsonarbuoy/bwctl": "pscheduler/iperf3",
    "perfsonarbuoy/owamp": "pscheduler/powstream",
    "traceroute": "pscheduler/traceroute"    
}

TOOL_EVENT_TYPES = {
    "pscheduler/iperf3": ["throughput"],
    "pscheduler/powstream": ["packet-loss-rate", "histogram-owdelay"],
}

PROM_CONFIG = {
    "pscheduler/iperf3" : [
        {
            "description": "PerfSONAR Throughput",
            "eventType": "throughput",
            "class": GaugeMetricFamily,
            "summaries": ["base"]
        },
        {
            "description": "PerfSONAR Throughput Failures",
            "eventType": "failures",
            "class": GaugeMetricFamily,
            "summaries": ["base"]
        },
        
    ],
    "pscheduler/powstream" : [
        {
            "description": "PerfSONAR Packet Loss Rate",
            "eventType": "packet-loss-rate",
            "class": GaugeMetricFamily,
            "summaries": ["base", "300"]
        },
        {
            "description": "PerfSONAR One-way Delay",
            "eventType": "histogram-owdelay",
            "class": HistogramMetricFamily,
            "summaries": ["base"]
        }
    ]
}
