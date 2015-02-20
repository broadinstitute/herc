# Introduction and environment

These scripts do the following:

* Download and install Aurora 0.7.0-incubating on the Mesosphere master;
* Build the Thermos executor, package and transfer it to the Mesos slaves; and
* Start up the Aurora scheduler and Thermos observer on the Mesosphere master.

They assume the following:

* You're running on [Mesosphere for Google Cloud Platform](http://google.mesosphere.com). The cluster I use is their Development Cluster: 4 slaves and 1 master.
* You are running on a \*nix machine not part of the Mesosphere cluster, but with your ssh authorized_keys set up.
* You should know the external IPs for your Mesosphere master and slave nodes.
* You have `mesos.native` and `mesos.interface` Python eggs built for the Mesosphere platform (Debian Wheezy at the time of writing). If you don't, follow the steps below to build the mesos 0.20.1 eggs.

# Building the `mesos.native` and `mesos.interface` Python eggs

Mesosphere supplies the `mesos` module egg for the Mesos version they're currently running, but not the `mesos.native` or `mesos.interface` egg. Apache Aurora has `mesos.native` eggs for Ubuntu and CentOS on [their SVN](https://svn.apache.org/repos/asf/incubator/aurora/3rdparty/), but at the time of writing Mesosphere is running Debian Wheezy and the Ubuntu eggs aren't compatible.

This means you have to compile Mesos from source yourself. Cribbing from the [make-mesos-native-egg](https://github.com/apache/incubator-aurora/blob/master/build-support/python/make-mesos-native-egg) script in the Aurora repo, this was basically a case of spinning up a Debian Wheezy Docker container with a mount to the underlying filesystem and running:

```bash
wget --progress=dot "https://archive.apache.org/dist/mesos/0.20.1/mesos-0.20.1.tar.gz"
tar zxvf mesos-0.20.1.tar.gz
cd mesos-0.20.1
./configure --disable-java
make
```

This will fail because you'll be missing some dependency. `sudo apt-get` it and try again. Repeat until it works. Breathe a sigh of relief and mop up your tears of anguish. `find` the .eggs and copy them "out" of the Docker container via the mount.

I believe the `mesos.interface` module is pure Python and available on PyPi but if you do the above you'll build your own egg for it anyway.

# Running these build and deploy scripts

Take your `mesos.native` and `mesos.interface` and put them in the same directory as these scripts. Then, the build and deploy process *should* be as simple as:

```bash
$ ./aurora_mesosphere_setup.sh master_ip slave1_ip slave2_ip slave3_ip slave4_ip
```

I'll walk through what they do here anyway.

### The build process

`aurora_mesosphere_setup.sh` first copies over the install scripts and Python eggs over to the Mesos master, where it'll download and install Aurora.

The main bulk of the work is done in `aurora_install.sh`, which is run on the Mesos master. This:

* Installs some dependencies from apt required to build Aurora.
* Sets up `$JAVA_HOME` and `$AURORA_HOME` environment variables.
* Builds Aurora. Note that there's some `chgrp` and `chmod` work to do to give the Mesosphere user `jclouds` permission to write to the `$AURORA_HOME` directory.
* Before building the client or Thermos executor + observer, we make `pants` do a no-op so that it bootstraps its own virtualenv. This is necessary because we need to install the `mesos` egg (from Mesosphere) and `mesos.interface` egg (built from source above, or from PyPi). It might be sufficient to just put them in `aurora-src/third_party`; I didn't try.
* After building the Aurora client we also create `/etc/aurora/clusters.json` so it knows what clusters exist. This is handled by `aurora_install_clustersjson.sh`.
* Before building the Thermos executor we put the `mesos.native` egg (built from source above) into the `third_party` folder. After building the executor we create the Thermos runner+executor `.pex` file, and put it in a tarball with the GC executor, both of which need to be installed on the slave nodes.

Everything that needs building is now built. All that remains is to set up the slave nodes and launch Aurora.

`aurora_mesosphere_setup.sh` pulls down the Thermos and GC executor tarball and puts it on the slave nodes in a directory known to the `aurora_scheduler_startup.sh` script.

This script:

* Specifies the default cluster name
* Specifies the location of the Thermos and GC executor
* Initialises the mesos-log
* Runs the scheduler in a `while` loop so that it restarts when it goes down for log compaction

The final step is to run `aurora_startup.sh` on the master node, which starts up both the Aurora scheduler and the Thermos observer.