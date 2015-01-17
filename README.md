# herc

1. Hercules, the Hero who saved Prometheus.
2. Thomas "Herc" Hauk, meatheaded police officer from *The Wire*:

![](http://upload.wikimedia.org/wikipedia/en/1/12/The_Wire_Herc.jpg)

herc uses [Apache Aurora](http://aurora.incubator.apache.org/) to schedule jobs running on an [Apache Mesos](http://mesos.apache.org/) cluster.

## Installation

For now, the easiest way to get herc running is by spinning up a cluster on [Mesosphere](https://google.mesosphere.com/).

Once the cluster has finished spinning up, the `mesosphere_setup` folder has a shell script that will install Aurora for you. It currently spins up one Aurora scheduler (on the Mesos master) and assumes all the other nodes are slaves.

From the machine that you gave Mesosphere the ssh_keys for:

```
$ git clone https://github.com/broadinstitute/herc.git
$ cd mesosphere_setup

# use the External IPs listed in your Mesosphere cluster's page.
$ ./aurora_mesosphere_setup.sh master_ip slave1_ip slave2_ip slave3_ip ... slaveN_ip
```

## Running

Once this is done you can ssh into the master node and start running jobs. This one will sleep for 5 seconds and then print `Hello herc!` to stdout:

```
$ ssh jclouds@master_ip
---
$ aurora job create herc/jclouds/devel/testJob testjob.aurora
```

## Other examples

If you want to test Aurora's ability to schedule lots of jobs, `batchjob.aurora` will do the trick:

```
aurora job create --bind time=2 --bind ninst=1000 --bind jn=1k herc/jclouds/devel/batchJob_1k batchjob.aurora
```

This job sleeps and then prints the job number to stdout. There are three parameters to this job:

* `time`: the length of time to sleep.
* `ninst`: the number of tasks to launch.
* `jn`: the name of the job to run. Note that this has to be appended to the last part of the Aurora job ID, so a jn=foo means the job ID would be herc/jclouds/devel/batchJob_jn.

You can then visit the Aurora scheduler and watch the jobs stack up and finish. You'll need to connect to the VPN provided by Mesosphere, and then go to the master's internal IP:8080 in your browser.
