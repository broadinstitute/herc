# http://phusion.github.io/baseimage-docker/
FROM phusion/baseimage

# Herc's default port
EXPOSE 4372

# This is so some tools don't crash (namely htop)
ENV TERM=xterm-256color

# Use baseimage's init system.
CMD ["/sbin/my_init"]

# Install Herc
ADD . /herc
RUN add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) multiverse" && \
    apt-get update && \
    apt-get install -y python2.7 python2.7-dev python-virtualenv
RUN virtualenv /herc_venv
RUN ["/bin/bash", "-c", "/herc/docker/install.sh /herc /herc_venv"]

# Add Herc as a service (it will start when the container starts)
RUN mkdir /etc/service/herc
ADD docker/run.sh /etc/service/herc/run

# These next 4 commands are for enabling SSH to the container.
# id_rsa.pub is referenced below, but this should be any public key
# that you want to be added to authorized_keys for the root user.
# Copy the public key into this directory because ADD cannot reference
# Files outside of this directory

#EXPOSE 22
#RUN rm -f /etc/service/sshd/down
#ADD id_rsa.pub /tmp/id_rsa.pub
#RUN cat /tmp/id_rsa.pub >> /root/.ssh/authorized_keys

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
