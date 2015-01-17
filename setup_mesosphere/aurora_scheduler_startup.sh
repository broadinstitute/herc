#!/usr/bin/env bash
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

# Scheduler launch script adapted from the examples/scheduler/scheduler-local.sh
# Edited to use $AURORA_HOME, which we set in /etc/profile.

# Flags that control the behavior of the JVM.
JAVA_OPTS=(
  -server
  -Xmx2g
  -Xms2g

  # Location of libmesos-XXXX.so / libmesos-XXXX.dylib
  -Djava.library.path=/usr/local/lib
)

# Flags control the behavior of the Aurora scheduler.
# For a full list of available flags, run bin/aurora-scheduler -help
AURORA_FLAGS=(
  -cluster_name=herc

  # Ports to listen on.
  -http_port=8081

  -native_log_quorum_size=1

  -zk_endpoints=localhost:2181
  -mesos_master_address=zk://localhost:2181/mesos

  -serverset_path=/aurora/scheduler

  -native_log_zk_group_path=/aurora/replicated-log

  -native_log_file_path="$AURORA_HOME/scheduler/db"
  -backup_dir="$AURORA_HOME/backups"

  -thermos_executor_path=/home/jclouds/thermos/thermos_executor.sh
  -gc_executor_path=/home/jclouds/thermos/gc_executor.pex

  -vlog=INFO
  -logtostderr
)

# Environment variables control the behavior of the Mesos scheduler driver (libmesos).
export GLOG_v=0
export LIBPROCESS_PORT=8083

JAVA_OPTS="${JAVA_OPTS[*]}" exec "$AURORA_HOME/bin/aurora-scheduler" "${AURORA_FLAGS[@]}"