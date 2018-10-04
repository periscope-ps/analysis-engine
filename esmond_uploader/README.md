# Esmond Uploader

Service to run that pulls esmond testing data based on a mesh-config and puts it into a desired UNIS instance as metadata.

## Usage
```
usage: esmond_uploader [-h] [-a ARCHIVE] [-u UNIS] [-m MESH] [-l LOG]
                       [-c CONFIG]

Service for grabbing test results out of Esmond and inserting them into UNIS

optional arguments:
  -h, --help            show this help message and exit
  -a ARCHIVE, --archive ARCHIVE
                        The HOST URL or IP of the testing archive
  -u UNIS, --unis UNIS  The UNIS url to use for saving and tracking testing
                        results.
  -m MESH, --mesh MESH  URL of the Meshconfig for the tests to track.
  -l LOG, --log LOG     Path to log file
  -c CONFIG, --config CONFIG
                        Path to configuration file.
```

Run with flags -
```
esmond_uploader -u http://localhost:8888 -m http://iu-mca01.osris.org/pub/config/state-mesh -a http://iu-ps01.osris.org
```

Run with conf file -
```
esmond_uploader -c esmond_uploader.conf
```

## Notes

Currently supports attaching testing data for paths of 1 Hop. The tool cannot discern what the realized path for traffic is - it only knows there is a test from A -> D, with no knowledge of what resources B and C are. So ensure the mesh-config you are watching is not trying to test a path with more than 3 links between a source to destination resource.

TODO:
- Add more error handling for bad mesh-config or failed unis topology resources.
