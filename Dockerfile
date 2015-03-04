# http://phusion.github.io/baseimage-docker/
FROM phusion/baseimage

# Herc's default port
EXPOSE 4372

# This is so some tools don't crash (namely htop)
ENV TERM=xterm-256color

# Use baseimage's init system.
CMD ["/sbin/my_init"]

# Install Herc.  Note the 'ensurepip' stuff below is to fix Ubuntu's broken Python 3 installation
ADD . /herc
RUN add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) multiverse" && \
    apt-get update && \
    apt-get install wget && \
    wget http://d.pr/f/YqS5+ -O ensurepip.tar.gz && \
    tar -xvzf ensurepip.tar.gz && \
    cp -r ensurepip $(python3 -c 'import sys; print(sys.path[1])') && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /ensurepip*

RUN pyvenv-3.4 /herc_venv
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
