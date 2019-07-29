import sys, logging, daemon, time, datetime, requests, argparse, json, traceback
from time import gmtime, strftime
from threading import Thread
from configparser import ConfigParser

from esmond_test import ThroughputTest, HistogramOWDelayTest, EsmondTest
from unis import Runtime
from settings import MESH_TO_PSTOOL, DEF_INTERVAL

MESH_TESTS = {
    "perfsonarbuoy/bwctl": ThroughputTest,
    "perfsonarbuoy/owamp": HistogramOWDelayTest,
    "traceroute": EsmondTest
}

class TestingDaemon:
    
    def __init__(self, conf, log_file="logs/esmond_uploader.log"):
        self.conf           = conf
        self.archive_url    = conf['archive_url']
        self.log_file       = conf['log_file']
        self.unis           = conf['unis']
        self.mesh_config    = conf['mesh_config'] 
        self.jobs           = []
        self.threads	    = []
        logging.basicConfig(filename=self.log_file, level=logging.INFO)
        logging.info('Log Initialized.')

    def _log(self, msg):
        now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        return logging.info(msg + " | " + now)    

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
            logging.info("COULD NOT CONNECT TO UNIS")
            raise AttributeError("COULD NOT CONNECT TO UNIS")
            sys.exit(0)
            
        # Setup jobs based on global mesh config
        try:
            mesh = requests.get(self.mesh_config).json()
        except:
            print("could not get mesh config. ensure url is correct.")

        self.mesh = mesh
        # make sure we merge global MAs
        gMA = mesh.get('measurement_archives', None)
        for test in mesh['tests']:
            test_type = test['parameters']['type']
            if not test.get('archive', None):
                test['archive'] = list()
                for ma in gMA:
                    if ma['type'] == test_type:
                        test['archive'].append(ma)
            self.jobs.append(test)
    
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
            print (job)
            members = job['members']['members']
            job_type = job['parameters']['type']
            tool = MESH_TO_PSTOOL.get(job_type, None)
            if not tool or job_type not in MESH_TESTS.keys():
                continue

            self._log("Init thread for " + job['description'])
            if len(members) > 2:
                pairs = [(member1, member2) for member1 in members for member2 in members]
                [print(p) for p in pairs]
                for p in pairs:
                    if p[0] == p[1]:
                        continue
                    test_thread = Thread(target=self._esmond_thread, args=(job, job_type, tool, p[0], p[1])).start()
                    if test_thread is not None:
                        self.threads.append(test_thread)
            
    def _esmond_thread(self, job, job_type, tool, member1, member2):
        description     = job['description']
        archives        = job['archive']
        source          = member1
        destination     = member2 
        interval        = job['parameters']['interval'] if 'interval' in job['parameters'] else DEF_INTERVAL
        
        logging.info("Initializing {} for {} -> {}".format(tool, source, destination))
        run = MESH_TESTS[job_type](description, tool, source, destination, archives, runtime=self.rt)
        logging.info("LOG: %s test thread - updating every %s seconds.\n Src: %s, Dst: %s", tool, interval, source, destination)
        while True:
            print("Attempting to fetch " + tool + " for "  + source + " -> " + destination)
            data = run.fetch(upload=False)
            print (data)
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

def main():
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

if __name__ == "__main__":
    main()
