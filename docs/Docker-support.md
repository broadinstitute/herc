Aurora currently doesn't support passing any options to Docker other than the image name. They have open issues to expose [networking modes](https://issues.apache.org/jira/browse/AURORA-1095), [custom mounts](https://issues.apache.org/jira/browse/AURORA-1107), and to allow [privileged containers](https://issues.apache.org/jira/browse/AURORA-1057).

#Automounts

Inside the Docker container, Aurora will define the variable `$MESOS_SANDBOX` as `/mnt/mesos/sandbox/` and mount it to that job's `sandbox` directory on the Mesos slave. Anything outside that path will vanish when the container is stopped.

This is a moot point anyway, since the job should take care of uploading its results somewhere safe. Aurora doesn't guarantee that things in the `sandbox` directory will stick around - indeed, the gc executor will clean them up eventually anyway.

#Networking

Aurora runs the docker container in host networking mode, meaning that any ports exposed on the host will be visible inside the container.