# http://phusion.github.io/baseimage-docker/
FROM phusion/baseimage

EXPOSE 4372
ENV TERM=xterm-256color

# Use baseimage's init system.
CMD ["/sbin/my_init"]

ADD . /herc

RUN add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) multiverse"
RUN apt-get update
RUN apt-get install -y python2.7 python2.7-dev python-virtualenv
RUN virtualenv /herc_venv
RUN cd /herc && python setup.py install

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
