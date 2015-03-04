# http://phusion.github.io/baseimage-docker/
FROM phusion/baseimage

# Herc's default port
EXPOSE 4372

# This is so some tools don't crash (namely htop)
ENV TERM=xterm-256color

# Use baseimage's init system.
CMD ["/sbin/my_init"]

# Install Herc.
ADD . /herc
RUN add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) multiverse" && \
    apt-get update && \
    apt-get install wget && \

    # Note that the next two commands is here to fix Ubuntu's broken Python 3 installation.
    # for some crazy reason, the 'ensurepip' module in missingPython's default installation location.
    # This causes pyvenv-3.4 to fail.  This hack downloads the module and installs it to the right
    # place in /usr/lib/python3.4.
    #
    # (see: https://bugs.launchpad.net/ubuntu/+source/python3.4/+bug/1290847)
    wget http://d.pr/f/YqS5+ -O /usr/lib/python3.4/ensurepip.tar.gz && \
    tar -xvzf /usr/lib/python3.4/ensurepip.tar.gz && \

    # Clean up intermediate files to keep the docker images small
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/lib/python3.4/ensurepip.tar.gz

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
