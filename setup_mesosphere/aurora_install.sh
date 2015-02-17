#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Aurora build script, adapted from examples/vagrant/aurorabuild.sh and https://aurora.apache.org/documentation/latest/deploying-aurora-scheduler/
# Edited to ditch the vagrant and upstart dependencies, and install requirements from a clean Google Mesosphere build.
# To be run on the Mesosphere Master.

#Install prerequisites from apt and set up env variables.
function install_prereqs {
  echo "Installing Aurora prerequisite packages from apt. This is going to take a while, and spam a lot to the screen."
  echo ""
  echo ""
  sleep 1
  sudo apt-get install build-essential openjdk-7-jdk screen python-dev libcurl4-openssl-dev libsasl2-dev

  echo ""
  echo ""
  echo "Setting up environment variables JAVA_HOME and AURORA_HOME."
  #Set up JAVA_HOME for Java7, and AURORA_HOME for our upcoming location of aurora-scheduler.
  sudo sh -c 'cat <<EOF >> /etc/profile
JAVA_HOME="/usr/lib/jvm/java-7-openjdk-amd64"
export JAVA_HOME
AURORA_HOME="/usr/local/aurora-scheduler"
export AURORA_HOME
EOF'
  
  mkdir aurora-src
  echo "Prerequisites installed."
}


install_prereqs
source /etc/profile

MESOS_VERSION="0.20.1"
DIST_DIR=~/aurora-src/dist

#Building the Aurora scheduler proper.
function build_scheduler {
  echo "Downloading the Aurora repo and building the scheduler. This will also take a while, and spam a lot."
  echo ""
  echo ""
  sleep 1
  git clone -b 0.7.0-incubating --single-branch https://github.com/apache/incubator-aurora.git aurora-src
  pushd aurora-src
  ./gradlew distZip

  sudo unzip $DIST_DIR/distributions/aurora-scheduler-*.zip -d /usr/local
  sudo ln -nfs "$(ls -dt /usr/local/aurora-scheduler-* | head -1)" /usr/local/aurora-scheduler

  #Set permissions on the AURORA_HOME directory.
  sudo addgroup aurora
  sudo usermod -a -G aurora jclouds
  sudo chgrp -R aurora "$AURORA_HOME/"
  sudo chmod -R 775 $AURORA_HOME
  
  #Let pants boostrap itself by asking it to do a no-op
  ./pants goals
  #Install Mesos Python packages to the pants venv
  source build-support/pants.venv/bin/activate
  easy_install http://downloads.mesosphere.io/master/debian/7/mesos-${MESOS_VERSION}-py2.7-linux-x86_64.egg
  easy_install ~/mesos.interface-${MESOS_VERSION}-py2.7.egg
  deactivate
  popd
}

#Builds the Aurora client.
function build_client {
  echo "Building the Aurora client."
  echo ""
  echo ""
  sleep 1
  pushd aurora-src
  ./pants binary src/main/python/apache/aurora/client/cli:aurora
  sudo ln -sf $DIST_DIR/aurora.pex /usr/local/bin/aurora
  popd
  
  sudo bash ./aurora_install_clustersjson.sh
}

#Builds the Aurora admin client.
function build_admin_client {
  echo "Building the Aurora admin client."
  echo ""
  echo ""
  sleep 1
  pushd aurora-src
  ./pants binary src/main/python/apache/aurora/admin:aurora_admin
  sudo ln -sf $DIST_DIR/aurora_admin.pex /usr/local/bin/aurora_admin
  popd
}

#Builds the Thermos task executor, and Aurora GC executor for distribution to slave nodes.
function build_executor {
  echo "Building the Thermos executor and packaging it up in a tarball for later distribution to slave nodes."
  echo ""
  echo ""
  sleep 1

  pushd aurora-src
  
  #Get mesos.native egg from Aurora SVN so thermos etc. can install. Note that this is Ubuntu, which *should* be compatible with Debian. But for safekeeping, the herc GitHub repo also contains a copy of the egg built on one of the Mesosphere GCE nodes.
  mkdir third_party
  pushd third_party
  cp ~/mesos.native-${MESOS_VERSION}-py2.7-linux-x86_64.egg .
  popd
  
  ./pants binary src/main/python/apache/aurora/executor/bin:gc_executor
  ./pants binary src/main/python/apache/aurora/executor/bin:thermos_executor
  ./pants binary src/main/python/apache/thermos/bin:thermos_runner

  # Package runner within executor.
  python <<EOF
import contextlib
import zipfile
with contextlib.closing(zipfile.ZipFile('dist/thermos_executor.pex', 'a')) as zf:
  zf.writestr('apache/aurora/executor/resources/__init__.py', '')
  zf.write('dist/thermos_runner.pex', 'apache/aurora/executor/resources/thermos_runner.pex')
EOF

  chmod +x $DIST_DIR/thermos_executor.pex
  
  pushd $DIST_DIR
  tar -cvf ~/thermos.tar thermos_executor.pex gc_executor.pex
  popd
  
  popd
}

#Builds the Thermos observer.
function build_observer {
  echo "Building the Thermos observer."
  echo ""
  echo ""
  sleep 1
  pushd aurora-src
  ./pants binary src/main/python/apache/thermos/observer/bin:thermos_observer
  popd
}

#Build everything.
build_scheduler
build_client
build_admin_client
build_executor
build_observer

echo "All installation on master node complete."
