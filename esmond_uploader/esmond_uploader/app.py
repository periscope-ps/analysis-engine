import sys, logging, daemon, time, datetime, requests, argparse, json, traceback
from time import gmtime, strftime
from threading import Thread
from configparser import ConfigParser
from logging import handlers
from collections import defaultdict, OrderedDict

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY

from unis import Runtime
from .esmond_test import MeshEntry, ArchiveTest
from .settings import *
from .utils import UnisUtil

log = logging.getLogger("app")

class TestingDaemon:
    def __init__(self, conf):
        self.conf           = conf
        self.log_file       = conf['log_file']
        self.unis           = conf['unis_url']
        self.archive        = conf['archive_url']
        self.mesh           = conf['mesh_url']
        self.interval       = conf['interval']
        self.prom           = conf['prometheus']
        self.verbose        = conf['verbose']
        self.quiet          = conf['quiet']
        self.jobs           = []
        self.threads	    = []
        self.metadata       = None
        self.data           = defaultdict(dict)
        
        # Setup logging
        form  = '[%(asctime)s] [%(threadName)s] %(levelname)s: %(msg)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        level = logging.CRITICAL if self.quiet else level

        if self.log_file == "stdout":
            fh = logging.StreamHandler(sys.stdout)
        else:
            fh = logging.handlers.RotatingFileHandler(
                self.log_file, maxBytes=(1024*1024*8), backupCount=7)
        fh.setFormatter(logging.Formatter(form))
        log.addHandler(fh)
        log.setLevel(level)
        
        if not self.archive and not self.mesh:
            log.error("No MA or Mesh URLs given, exiting!")
            sys.exit(1)

        if self.prom:
            try:
                start_http_server(PROM_PORT)
            except OSError as e:
                log.error("Could not start Prometheus exporter: {}".format(e))
                sys.exit(1)
            REGISTRY.register(self)

    def _merge_data(self, orig, new):
        for k,v in new.items():
            if (k in orig and isinstance(orig[k], dict)):
                self._merge_data(orig[k], new[k])
            else:
                orig[k] = new[k]
            
    # Prometheus collect routine
    def collect(self):
        labels = ['src', 'dst', 'tool', 'summary']
        cls = dict()
        
        # first create the metric classes
        for k in PROM_CONFIG.keys():
            for p in PROM_CONFIG[k]:
                et = p['eventType']
                cls[et] = p['class']("perfsonar_"+et.replace("-", "_"), p['description'], labels=labels)

        # now add some metrics from our stored esmond data
        for j in self.jobs:
            tool = j['tool-name']
            src = j['input-source']
            dst = j['input-destination']
            key = j['metadata-key']

            if tool in PROM_CONFIG.keys():
                pconf = PROM_CONFIG[tool]
                for p in pconf:
                    et = p['eventType']
                    if cls[et].type == "gauge":
                        for s in p['summaries']:
                            try:
                                vals = self.data[key][et][s]
                                for v in vals:
                                    # convert non-number values to binary 1
                                    if isinstance(v['val'], dict) or isinstance(v['val'], str):
                                        val = 1
                                    else:
                                        val = v['val']
                                    cls[et].add_metric([src, dst, tool, s], val)
                                yield cls[et]
                            except:
                                continue
                    elif cls[et].type == "histogram":
                        for s in p['summaries']:
                            try:
                                vals = self.data[key][et][s]
                                for entry in vals:
                                    buckets = []
                                    cnt = 0
                                    summ = 0
                                    od = OrderedDict(sorted(entry['val'].items()))
                                    for k,v in od.items():
                                        buckets.append((k,v))
                                        summ += (float(k) * v)
                                        cnt += v
                                    buckets.append(('+Inf', cnt))
                                    cls[et].add_metric([src, dst, tool, s], buckets, summ)
                                yield cls[et]
                            except:
                                pass
                
    def _setup_archive(self):
        log.info("Using esmond MA URL to initialize jobs")
        meta = self.metadata
        for test in meta:
            tool = test.get('tool-name', None)
            # filter test types we care about
            if not tool or tool not in TOOL_EVENT_TYPES.keys():
                continue
            test['archive'] = self.archive
            self.jobs.append(test)
            
    def _setup_mesh(self):
        log.info("Using MeshConfig URL to initialize jobs")
        mesh = self.metadata
        gMA = mesh.get('measurement_archives', None)
        
        for test in mesh['tests']:
            job_type = test['parameters']['type']
            tool = MESH_TO_PSTOOL.get(job_type, None)
            
            # filter test types we care about
            if not tool or job_type not in MESH_TESTS:
                continue

            # update archive URLs
            test_type = test['parameters']['type']
            archives = []
            for ma in gMA:
                if ma['type'] == test_type:
                    archives.append(ma)
            
            # set testing pairs
            members = test['members']['members']
            if len(members) > 2:
                pairs = [(member1, member2) for member1 in members for member2 in members]
                for p in pairs:
                    if p[0] == p[1]:
                        continue
                    # turn a mesh testing pair into metadata we can query for data
                    mt = MeshEntry(tool, p[0], p[1], archives)
                    meta = mt.get_metadata()
                    if len(meta) == 1:
                        test = meta[0]
                        test['archive'] = mt.get_archive()
                        self.jobs.append(test)
                    else:
                        log.debug("No measurement metadata found for {} / {} -> {}".
                                  format(tool, p[0], p[1]))
            
    def _setup(self):
        '''
	Setup the main service. 
	- read and apply config in Meshconfig document.
	- connect to Runtime
	Exit if configuration fails.
        '''			
        try:
            self.rt = Runtime(self.unis)
            self.rt.addService("unis.services.data.DataService")
        except Exception as e:
            log.error("Could not connect to UNIS!")
            sys.exit(1)

        url = self.archive if self.archive else self.mesh
        # Setup jobs based on global mesh config
        try:
            self.metadata = requests.get(url).json()
        except:
            log.error("Could not get job metadata from {}, ensure URL is correct".format(url))
            sys.exit(1)
            
        if self.archive:
            self._setup_archive()
        else:
            self._setup_mesh()
    
    def start(self):
        log.info("Config - \n\
	  Archive Host: {}\n\
	  UNIS: \t{}\n\
	  Mesh: \t{}\n\
          Interval: \t{}\n\
          Prometheus: \t{}".format(self.archive,
                                   self.unis,
                                   self.mesh,
                                   self.interval,
                                   self.prom))

        # Get a list of jobs to execute based on the config
        self._setup()
        
        log.info("Starting jobs [{}]".format(len(self.jobs)))
        for job in self.jobs:
            th = Thread(target=self._archive_thread, args=(job,)).start()
            if th is not None:
                self.threads.append(th)

    def _archive_thread(self, job):
        source = job['source']
        destination = job['destination']
        tool = job['tool-name']
        key = job['metadata-key']
        archive = job['archive']
        
        util = UnisUtil(rt=self.rt)
        
        run = ArchiveTest(archive, job)
        while True:
            has_data, data = run.fetch()
            
            log.info("Completed {} for {} -> {}, waiting {}".format(tool,
                                                                    source,
                                                                    destination,
                                                                    self.interval))
            
            
            util.upload_data(data, job, source, destination, archive)
            
            self._merge_data(self.data[key], data)
            time.sleep(self.interval)

def _read_config(file_path):
    if not file_path:
        return {}
    parser = ConfigParser(allow_no_value=True)
    
    try:
        parser.read(file_path)
    except Exception:
        raise AttributeError("INVALID FILE PATH FOR STATIC RESOURCE INI.")
        return

    config = parser['CONFIG']
    try:
        result = {'unis_url'   : config['unis_url'],
                  'archive_url': config['archive_url'],
                  'mesh_url'   : config['mesh_url'],
                  'log_file'   : config['log_file'],
                  'interval'   : int(config['interval'])}
        
        return result

    except Exception as e:
        raise AttributeError('Error in config file, please ensure file is '
                             'formatted correctly and contains values needed.')

def main():
    parser = argparse.ArgumentParser(description='Service for grabbing test results out of Esmond and inserting them into UNIS')
    parser.add_argument('-a', '--archive', default=None, type=str, help='The complete URL of an esmond MA')
    parser.add_argument('-u', '--unis', type=str, help="The UNIS url to use for saving and tracking testing results.")
    parser.add_argument('-m', '--mesh', default=None, type=str, help="URL of a pS MeshConfig (instead of MA URL)")
    parser.add_argument('-p', '--prometheus', action='store_true', help='Enable Prometheus collector')
    parser.add_argument('-l', '--log', default="/var/log/esmond_uploader.log", help="Path to log file")
    parser.add_argument('-i', '--interval', default=None, help="Global polling interval in seconds")
    parser.add_argument('-c', '--config', default=None, type=str, help="Path to configuration file.")
    parser.add_argument('-v', '--verbose', action='store_true', help='Produce verbose output from the app')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode, no logging output')
    
    args = parser.parse_args()
    
    conf = {'unis_url': args.unis,
            'archive_url': args.archive,
            'mesh_url': args.mesh,
            'log_file': args.log,
            'interval': args.interval}
    conf.update(**_read_config(args.config))
    conf.update(**{k:v for k,v in args.__dict__.items() if v is not None})

    # use a default polling interval if not set
    if not conf['interval']:
        conf['interval'] = DEF_INTERVAL
    
    app = TestingDaemon(conf)
    app.start()

if __name__ == "__main__":
    main()
