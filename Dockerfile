# http://phusion.github.io/baseimage-docker/
FROM phusion/baseimage

# Herc's default port
EXPOSE 4372

# This is so some tools don't crash (namely htop)
ENV TERM=xterm-256color
ENV HERC_SRC=/herc
ENV HERC_VENV=/herc_venv
ENV LANG=en_US.UTF-8

# Use baseimage's init system.
CMD ["/sbin/my_init"]

# Install Herc.
RUN add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) multiverse" && \

    # Note that the next command is here to fix Ubuntu's broken Python 3 installation.
    # For some crazy reason, the 'ensurepip' module in missing in Python's default installation
    # location.  This causes pyvenv-3.4 to fail.  This hack downloads the module and installs
    # it to the right place in /usr/lib/python3.4.
    #
    # (see: https://bugs.launchpad.net/ubuntu/+source/python3.4/+bug/1290847)
    curl -L http://d.pr/f/YqS5+ | tar xvz -C /usr/lib/python3.4

    # Clean up intermediate files to keep the docker images small
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ADD . $HERC_SRC
RUN pyvenv-3.4 $HERC_VENV
RUN ["/bin/bash", "-c", "/herc/docker/install.sh $HERC_SRC $HERC_VENV"]

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
