# herc

1. Hercules, the Hero who saved Prometheus.
2. Thomas "Herc" Hauk, meatheaded police officer from *The Wire*:

![](http://upload.wikimedia.org/wikipedia/en/1/12/The_Wire_Herc.jpg)

herc uses [Apache Aurora](http://aurora.incubator.apache.org/) to schedule jobs running on an [Apache Mesos](http://mesos.apache.org/) cluster.

The full documentation is in the [docs](docs/Home.md) folder; this is just a quick overview.

## Setting up Mesosphere

For now, the easiest way to get herc running is by spinning up a cluster on [Mesosphere](https://google.mesosphere.com/).

Once the cluster has finished spinning up, the `setup_mesosphere` folder has a shell script that will install Aurora for you. It currently spins up one Aurora scheduler (on the Mesos master) and assumes all the other nodes are slaves.

From the machine that you gave Mesosphere the ssh_keys for:

```
$ git clone git@github.com:broadinstitute/herc.git
$ cd setup_mesosphere

# use the External IPs listed in your Mesosphere cluster's page.
$ ./aurora_mesosphere_setup.sh master_ip slave1_ip slave2_ip slave3_ip ... slaveN_ip
```

## Installing herc

Herc runs on Python 2.7. It may be upgraded to Python 3 at some point, depending on where DSDE Engineering settles re Python standards.

On the Mesosphere master:

```
$ git clone git@github.com:broadinstitute/herc.git
$ virtualenv ve_herc
$ source ve_herc/bin/activate
$ python setup.py develop
$ screen -mdS herc bash -c 'source ve_herc/bin/activate && herc'
```

For foreground operation with debug logging to stdout, run herc as: `herc --debug`

### Running Herc in Docker

See detailed instructions [here](docs/Herc-in-Docker.md)

## API

The full list of endpoints provided by herc are always available at:

`GET https://localhost:4372/`

(4372 is HERC on a phone keypad, if you were wondering.)

At the time of writing, the endpoints are:

* `GET /` Returns a list of endpoints and brief descriptions. This is always accurate; the document you're reading now may not be!
* `GET /schema` Returns the JSON schema used to validate job submissions sent to `/submit`.
* `POST /submit` Expects a JSON body that validates against the schema returned by `/schema`. Returns a string, the job ID.
* `GET /status/<jobid>` Query Aurora and return the status of the job id. 404 if not found, otherwise will return JSON with the job's current status and the time it entered that status.
* `GET /sleep/<n>` Test endpoint that keeps the connection open for n seconds and then returns how long it was open for.

A deeper dive into the API is available [here](docs/API.md). 

## Watching it go

Connect to the VPN provided by Mesosphere. From there, there are two things to look at:

#### Aurora

`master_ip:8081/scheduler`

Shows Aurora details about your job. You'll be able to see if it got lost; most often this is because the executor wasn't correctly installed and Mesos gave up on it. In this case you'll see a bunch of failed jobs and an active job that's throttled for "flapping".

#### Mesos

`master_ip:5050`

Will show you the jobs that Mesos knows about, and allow you dig into the stderr and stdout files generated in the slave sandboxes.
