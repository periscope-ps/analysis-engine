from setuptools import setup, Command
import os

import sys

sys.path.append(".")
if sys.version_info[0] < 3 or sys.version_info[1] < 5:
    print("------------------------------")
    print("Must use python 3.5 or greater", file=sys.stderr)
    print("Found python verion ", sys.version_info, file=sys.stderr)
    print("Installation aborted", file=sys.stderr)
    print("------------------------------")
    sys.exit()

setup(
    name="esmond_uploader",
    version="0.1", 
    author="gskipper@iu.edu",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    
    dependency_links=[
        "git+https://github.com/periscope-ps/lace.git/@master#egg=lace",
        "git+https://github.com/periscope-ps/unisrt.git/@develop#egg=unisrt",
    ],
    install_requires=[
        "websockets==4.0.1",
        "lace",
        "unisrt",
        "requests",
        "python-daemon",
        "prometheus_client"
    ],
    entry_points = {
        'console_scripts': [
            'esmond_uploader = app:main'
	]
    }
)
