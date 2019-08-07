# Esmond Uploader

The uploader is a service that pulls esmond testing data based on a PWA
MeshConfig, or directly using a PerfSONAR MA URL, and exports it into the
desired UNIS or Prometheus instance(s).

## Setup

To run out of your source directory:
```
python3 setup.py develop
```

Then, `esmond_uploader` will be available in your path.

To avoid system-side python issues, try a VirtualEnv:

```
python3 -m venv <dir>
source <dir>/bin/activate
pip3 install docutils
python3 setup.py develop
```

Now everything for the uploader service will be installed in your venv at <dir>
and not use any system-wide imports.

## Usage
```
usage: esmond_uploader [-h] [-a ARCHIVE] [-u UNIS] [-m MESH] [-p] [-l LOG]
                       [-c CONFIG] [-v] [-q]

Service for grabbing test results out of Esmond and inserting them into UNIS

optional arguments:
  -h, --help            show this help message and exit
  -a ARCHIVE, --archive ARCHIVE
                        The complete URL of an esmond MA
  -u UNIS, --unis UNIS  The UNIS url to use for saving and tracking testing
                        results.
  -m MESH, --mesh MESH  URL of a pS MeshConfig (instead of MA URL)
  -p, --prometheus      Enable Prometheus collector
  -l LOG, --log LOG     Path to log file
  -c CONFIG, --config CONFIG
                        Path to configuration file.
  -v, --verbose         Produce verbose output from the app
  -q, --quiet           Quiet mode, no logging output

```

Example from the command line:
```
esmond_uploader -u http://localhost:8888 -a http://iu-ps01.osris.org/esmond/perfsonar/archive -p -l stdout
```

Run with configuration file:
```
esmond_uploader -c esmond_uploader.conf
```

## Prometheus Testing

The esmond collected values sent to Prometheus is configured in settings.py.
The default settings are a sane subset of values from most PerfSONAR measurement
archives.

Install Prometheus and Grafana using the Docker-compose stack from the following
link:

https://github.com/vegasbrianc/prometheus

Add a job config for esmond_uploader by editing `prometheus/prometheus.yml`:

```
- job_name: 'perfsonar'
  static_configs:
    - targets: ['localhost:8000']
```

Note that the esmond_uploader will start the Prometheus exporter server on port
8000.

Follow the instructions on starting the docker swarm.

Once Prometheus is running, navigate to http://localhost:9090/graph and submit
some queries.

Grafana will also be running at http://localhost:3000 with Prometheus as a data
source.
