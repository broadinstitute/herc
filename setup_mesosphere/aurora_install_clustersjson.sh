#!/bin/bash

#add clusters.json so aurora client knows where to find things
ips=$(hostname -I)
iparr=($ips)
myip=${iparr[0]}
  #sudo mkdir /etc/aurora
cat <<EOF > /etc/aurora/clusters.json
[{
  "name": "herc",
  "zk": "$myip",
  "scheduler_zk_path": "/aurora/scheduler",
  "auth_mechanism": "UNAUTHENTICATED",
  "slave_run_directory": "latest",
  "slave_root": "/var/lib/mesos"
}]
EOF