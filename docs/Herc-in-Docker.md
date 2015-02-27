Running Herc in Docker
======================

Note this is different from running Docker jobs through Herc.  This document refers to running a Herc server in a Docker container

Building the Docker image
-------------------------

The root of the repository contains a `Dockerfile` which builds off of the [baseimage](http://phusion.github.io/baseimage-docker/) Docker image.  Build it with `docker build`:

```bash
$ docker build .
...
Successfully built e8d27cf83b42
```

Running the Docker image
------------------------

The image should be run in the background.  It's configured to run an init process so it won't run to completion and exit immediately:

```bash
$ docker run -d -p 4372:4372 e8d27cf83b42
a309813b3de6dfce4c336d12df8199d5dd691a8253d4acc74be44e044c39113d
```

Once the image starts running, Herc will immediately be up and running.  The `-p 4372:4372` maps port 4372 to the host machine.  To test, run:

```bash
$ http --verify=no https://192.168.59.103:4372/
```

```http
HTTP/1.1 200 OK
Access-Control-Allow-Credentials: true
Access-Control-Allow-Origin: *
Content-Encoding: gzip
Content-Length: 331
Content-Type: application/json
Date: Fri, 27 Feb 2015 17:22:18 GMT
Etag: "1a5eae502514465d016ec0e4f63ced4e52ef348c"
Server: TornadoServer/4.1
Vary: Accept-Encoding

{
    "GET /": "Returns the list of endpoints that this webservice provides.",
    "GET /schema": "Returns the JSON schema used to validate job submission requests.",
    "GET /sleep/<n>": "Sleep for n seconds and then return.",
    "GET /status/<jobid>": "Query Aurora and return the status of this job. 404 if not found, otherwise will return JSON with the job's current status and the time it entered that status.",
    "POST /submit": "Submits a job request. Body must be JSON that validates against the JSON schema available at GET /schema. Returns a string, the job ID."
}
```

> **Note**: The above example uses the address `192.168.59.103` because I am using [boot2docker](http://boot2docker.io/) on Mac OS.
>
> If you're running Docker natively, use `docker ps` to get the Container ID, then find it's IP address by running:
>
> `docker inspect -f "{{ .NetworkSettings.IPAddress }}" <container_id>`

Getting a Shell on the Docker Container
---------------------------------------

There are two methods of doing this: `docker exec` or `ssh`

### Docker exec method

```bash
$ docker exec -t -i <CONTAINER ID> bash -l
root@a309813b3de6:/#
```

### SSH Method

This is more involved and arguably not very useful compared with docker exec method but for completeness I'll list how to do it:

Prior to building the Docker image, comment out the section in the Docker file related to forwarding port 22 and putting your public key on the host.  Read the comment on that section carefully.  It is important to *copy* your public key to the repository root before running `docker build`, as it can only accept relative paths.

After the Docker image is built, run it by forwarding a port on the host machine to port 22 on the Docker image:

```bash
$ docker run -d -p 42222:22 -p 4372:4372 7ad111ec49ef
```

Then SSH by specifying `-p 42222`:

```bash
$ ssh -p 42222 root@$(docker inspect -f "{{ .NetworkSettings.IPAddress }}" <container_id>)
```

#### Boot2Docker SSH Caveat

You might find that you [can't SSH to the virtual machine](http://stackoverflow.com/questions/23014684/how-to-get-ssh-connection-with-docker-container-on-osxboot2docker) hosting the Docker image.  If that's the case, stop boot2docker, then run:

```bash
$ VBoxManage modifyvm "boot2docker-vm" --natpf1 "containerssh,tcp,,42222,,42222"
```

Then, start back up boot2docker, and run the container in background mode, and SSH via:

```bash
$ ssh -p 42222 root@$(boot2docker ip)
```

Container Layout
----------------

![Docker Processes](http://i.imgur.com/3wEtmHb.png)

The container has an init process which spawns a `cron`, `syslog`, and (optionally) a `sshd` process.  Since the init process is always running, this Docker image should always be run in the background.

The container is also setup to use [runit](http://smarden.org/runit/) to manage services running in the container.  All of the `runsv` processes above are from RUnit.

All services for RUnit are in `/etc/service/`.  Herc is in `/etc/service/herc` where the `run` script tells RUnit how to start the process.  RUnit will also monitor the process and restart it if it goes down.

### Filesystem Structure

* `/herc` - Source code for Herc
* `/herc_venv` - Python virtual environment where Herc is installed
