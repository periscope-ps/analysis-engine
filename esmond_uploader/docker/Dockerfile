FROM python:3.6-stretch
LABEL version="1.0-0"

MAINTAINER Ezra Kissel <ezkissel@indiana.edu>

EXPOSE 8000/tcp

RUN apt-get update
RUN apt-get -y install sudo

RUN export uid=1000 gid=1000 && \
    mkdir -p /home/periscope && \
    echo "periscope:x:${uid}:${gid}:Periscope User,,,:/home/periscope:/bin/bash" >> /etc/passwd && \
    echo "periscope:x:${uid}:" >> /etc/group && \
    echo "periscope ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/periscope && \
    chmod 0440 /etc/sudoers.d/periscope && \
    chown ${uid}:${gid} -R /home/periscope

USER periscope
ENV HOME /home/periscope
WORKDIR $HOME

RUN git clone -b v2 https://github.com/periscope-ps/analysis-engine
RUN cd analysis-engine/esmond_uploader && sudo python3 setup.py install && cd -

CMD esmond_uploader -c /etc/periscope/esmond_uploader.conf -p
