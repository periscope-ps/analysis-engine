import sys, logging, daemon, time, datetime, requests, argparse, json, traceback
from time import gmtime, strftime
from threading import Thread
from configparser import ConfigParser

from unis import Runtime
from esmond_test import ThroughputTest, HistogramOWDelayTest

TESTS = { 'throughput': ThroughputTest,
          'latency':    HistogramOWDelayTest,
          'sdn-throughput': ThroughputTest,
          'Frontend Throughput': ThroughputTest,
          'Frontend Latency': HistogramOWDelayTest,
          'Backend Throughput': ThroughputTest,
          'Backend Latency': HistogramOWDelayTest,
          'perfsonarbuoy/owamp': HistogramOWDelayTest,
          "perfsonarbuoy/bwctl": ThroughputTest}

class TestingDaemon:
    
    def __init__(self, conf, log_file="logs/esmond_uploader.log"):
        self.conf           = conf
        self.archive_url    = conf['archive_url']
        self.log_file       = conf['log_file']
        self.unis           = conf['unis']
        self.mesh_config    = conf['mesh_config'] 
        self.jobs           = []
        self.threads		= []
        logging.basicConfig(filename=self.log_file, level=logging.INFO)
        logging.info('Log Initialized.')
 
        return

    def begin(self):
        logger = logging.getLogger()
        fh = logging.FileHandler(self.log_file)
        logger.addHandler(fh)

        self._setup()

        #with daemon.DaemonContext(files_preserve = [fh.stream]):
        logging.info("********** Esmond Uploader Utility **********")
            
        logging.info("MAIN THREAD \nConfig - \n\
				Archive Host:%s\n\
				Unis: %s\n\
				Mesh: %s", self.archive_url, self.unis, self.mesh_config)
        logging.info("Starting jobs") 
        
        for job in self.jobs: 
            
            self._log("Init thread for " + job['description'])
            
            if len(job['members']['members']) > 2:
                members = job['members']['members']
                pairs = [(member1, member2) for member1 in members for member2 in members]
                [print(p) for p in pairs]
                    
                for p in pairs:
                    test_thread = Thread(target=self._init_test_thread, args=(job,p[0],p[1],self.conf,)).start()
                    time.sleep(2)
                    if test_thread is not None:             
                        self.threads.append(test_thread)
                    else:
                        print("Thread for " + p[0] + "-" + p[1] + " none type thread")
        
        return 

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
            print(e)
            logging.info("COULD NOT CONNECT TO UNIS")
            raise AttributeError("COULD NOT CONNECT TO UNIS")
            sys.exit(0)
         
        
        self._handle_mesh()
        return
    
    def _handle_mesh(self):

        try:
            mesh = requests.get(self.mesh_config).json()
        except:
            print("could not get mesh config. ensure url is correct.")
            
        
        self.mesh = mesh
        for test in mesh['tests']:
            self.jobs.append(test)

        return
    
    def _log(self, msg):
        now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        return logging.info(msg + " | " + now)    

    def _init_test_thread(self, job, member1, member2, conf): 
        source          = member1
        destination     = member2 
        test_type       = job['description']
        interval        = job['parameters']['interval'] if 'interval' in job['parameters'] else 120 

        
        logging.info("Trying test for %s - %s", source, destination)
        
        try:
            if test_type not in TESTS.keys():
                return

            run = TESTS[test_type](self.archive_url, source=source, destination=destination, runtime=self.rt)
            self._log("THREAD OK")
        except Exception as e:    
            self._log("Test not defined for " + test_type + "| " + source + " - " + destination + ". Could not start thread")
            return
        
        logging.info("LOG: %s test thread - updating every %s seconds.\n Src: %s, Dst: %s", test_type, interval, source, destination)
        while True:
            print("Attempting to fetch " + test_type + " from "  + source + " -> " + destination)
            data = run.fetch(time_range=3600, upload=True) 
            if data is None:
                return print("Bad Thread")
            print("Fetch routine done, waiting for next interval")
            time.sleep(interval)

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
        result = {'unis': config['unis'],
                  'archive_url': config['archive_url'],
                  'mesh_config': config['mesh_config'],
                  'log_file': config['log_file']}
        
        return result

    except Exception as e:
        print(e)
        raise AttributeError('Error in config file, please ensure file is '
                             'formatted correctly and contains values needed.')
    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Service for grabbing test results out of Esmond and inserting them into UNIS')
    parser.add_argument('-a', '--archive', default=None, type=str, help='The HOST URL or IP of the testing archive')
    parser.add_argument('-u', '--unis', type=str, help="The UNIS url to use for saving and tracking testing results.")
    parser.add_argument('-m', '--mesh', default=None, type=str, help="URL of the Meshconfig for the tests to track.")
    parser.add_argument('-l', '--log', default="logs/esmond_uploader.log", help="Path to log file")
    parser.add_argument('-c', '--config', default=None, type=str, help="Path to configuration file.")
    
    args = parser.parse_args()
    
    conf = {'unis':args.unis, 'archive_url':args.archive, 'mesh_config':args.mesh, 'log_file':args.log}
    conf.update(**_read_config(args.config))
    conf.update(**{k:v for k,v in args.__dict__.items() if v is not None})
    print(conf)
    app = TestingDaemon(conf)
    print("Starting App")
    app.begin()

