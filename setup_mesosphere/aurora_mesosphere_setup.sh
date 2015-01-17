#!/bin/bash

#Usage: aurora_mesosphere_setup.sh master_ip slave1_ip slave2_ip slave3_ip etc...

if [ $# -eq 0 ]; then
	echo "Usage: aurora_mesosphere_setup.sh master_ip slave1_ip slave2_ip slave3_ip ... slaveN_ip"
	echo "These should be the External IPs listed on the Mesosphere cluster page."
	exit
fi

master_ip=$1
mesosuser="jclouds"
shift

echo "Copying over install files to Mesos master..."
echo ""
echo ""
scp aurora_install.sh aurora_install_clustersjson.sh aurora_scheduler_startup.sh aurora_startup.sh aurora_thermos_startup.sh ../jobdefs/testjob.aurora ../jobdefs/batchjob.aurora $mesosuser@$master_ip

echo ""
echo ""
echo "Running Aurora installation script on Mesos master..."
sleep 1
echo ""
echo ""

ssh $mesosuser@$master_ip ./aurora_install.sh

echo ""
echo ""
echo "Copying over the Thermos executor tarball from the master node."
sleep 1
echo ""
echo ""
scp $mesosuser@$master_ip:thermos.tar thermos.tar

echo ""
echo ""
echo "Copying and extracting the Thermos executor tarball to the slave nodes."
#This should be trivially parallelisable using something like pdsh, but I couldn't get it working quickly.
for slave_ip in "$@"; do
	echo "Setting up $slave_ip..."
	scp thermos.tar $mesosuser@$slave_ip:~/thermos.tar
	ssh $mesosuser@$slave_ip mkdir thermos; tar -C thermos -xvf thermos.tar
	echo ""
done

echo ""
echo ""
echo "Running the Aurora scheduler on the Mesos master."
ssh $mesosuser@$master_ip ./aurora_startup.sh

echo "All done!"
echo "You should now be able to SSH into the master node and run jobs, e.g.:"
echo ""
echo "\$ ssh $mesosuser@$master_ip"
echo "\$ aurora job create herc/jclouds/devel/testJob testjob.aurora"
