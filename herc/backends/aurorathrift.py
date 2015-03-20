import getpass
import json
from thrift.transport.THttpClient import THttpClient
from thrift.protocol.TJSONProtocol import TJSONProtocol
from gen.apache.aurora.api import AuroraSchedulerManager
from gen.apache.aurora.api.constants import AURORA_EXECUTOR_NAME
from gen.apache.aurora.api.ttypes import *
from .. import config

import logging
log = logging.getLogger(__name__)

# Resource size lookups
sizes = {
    "BYTES" : 1,
    "KB" : 1024,
    "MB" : 1024*1024,
    "GB" : 1024*1024*1024,
    "TB" : 1024*1024*1024*1024
}

class AuroraThrift(object):
    """Talk to the Aurora scheduler using its Thrift API."""
    def __init__(self):
        self.transport = THttpClient(config.get("aurorathrift.server"))
        self.protocol = TJSONProtocol(self.transport)
        self.transport.open()
        self.client = AuroraSchedulerManager.Client(self.protocol)
        self.localize_cmd = config.get("auroracli.localizecmd")

    @staticmethod
    def _build_process(name, cmd, final):
        """Builds a dict representing a process."""
        return {
            "daemon": False,
            "name": name,
            "ephemeral": False,
            "max_failures": 1,
            "min_duration": 5,
            "cmdline": cmd,
            "final": final
        }

    @staticmethod
    def _build_executor_config(jobid, jobrq, localize_cmd):
        """Builds a Python object representing the Task's ExecutorConfig."""
        exconf = {
            "environment" : config.get("aurora.cluster.env"),
            "container" : { 'docker' : { 'image' : jobrq['docker'] } },
            "name" : jobid,
            "service" : False,
            "max_task_failures" : 1,
            "cron_collision_policy" : "KILL_EXISTING",
            "priority": 0,
            "cluster": config.get("aurora.cluster.name"),
            "health_check_config": {
                "initial_interval_secs": 15,
                "interval_secs": 10,
                "timeout_secs": 1,
                "max_consecutive_failures": 0
            },
            "role": config.get("aurora.cluster.role"),
            "enable_hooks": False,
            "production": False,
            "constraints": { "host": "limit:99999999" }
        }

        task = {
            "name": jobid + '_task',
            "finalization_wait": 30,
            "max_failures": 1,
            "max_concurrency": 0,
            "resources": {
                 "disk": jobrq['resources']['disk'] * sizes[jobrq['resources']['diskunit']],
                 "ram" : jobrq['resources']['mem'] * sizes[jobrq['resources']['memunit']],
                 "cpu": jobrq['resources']['cpu']
             }
        }

        # processes to localize down from the "inputs" part of the schema
        downloads = [ AuroraThrift._build_process(
                            name = "locdown_" + str(idx),
                            cmd = localize_cmd + ' "' + path['cloud'] + '" "' + path['local'] + '"',
                            final = False)
                     for (idx, path) in enumerate(jobrq['inputs']) ]

        # processes to localize back up to the cloud from the "outputs" part of the schema
        uploads = [ AuroraThrift._build_process(
                        name = "locup_" + str(idx),
                        cmd = localize_cmd + ' "' + path['local'] + '" "' + path['cloud'] + '"',
                        final = False)
                   for (idx, path) in enumerate(jobrq['outputs'])]

        # list of processes: download inputs, run the commandline, upload outputs
        task['processes'] = downloads \
                             + AuroraThrift._build_process(name = jobid + '_ps', cmd = jobrq['commandline'], final = False) \
                             + uploads

        #order constraints of all processes so far - i.e. the non-final ones
        task['constraints'] = [ { "order" : [ p['name'] for p in task['processes'] ] } ]

        #finalizing processes to localize stdout and stderr up to gcs
        #these are guaranteed to run even if the task fails because one of the other processes fail.
        if jobrq['stdout'] != "":
            task['processes'].append(AuroraThrift._build_process(
                name = "__locup_stdout",
                cmd = localize_cmd + ' ' + config.get("aurora.sandboxdir") + '"/.logs/' + jobid + '_ps/0/stdout" "' + jobrq['stdout'] + '"',
                final = True))
        if jobrq['stderr'] != "":
            task['processes'].append(AuroraThrift._build_process(
                name = "__locup_stderr",
                cmd = localize_cmd + ' ' + config.get("aurora.sandboxdir") + '"/.logs/' + jobid + '_ps/0/stderr" "' + jobrq['stderr'] + '"',
                final = True))

        exconf['task'] = task
        return exconf

    def requestjob(self, jobid, jobrq):
        owner = Identity(role=config.get("aurora.cluster.role"), user=getpass.getuser())
        key = JobKey(
            role=config.get("aurora.cluster.role"),
            environment=config.get("aurora.cluster.env"),
            name=jobid)

        task = TaskConfig()

        # TODO: Need a better way of keeping these in sync with _build_executor_config
        task.jobName = jobid
        task.environment = config.get("aurora.cluster.env")
        task.production = False  # For now. If we ever have real production jobs with quota, we can set this.
        task.isService = False
        task.maxTaskFailures = 1
        task.priority = 0
        task.contactEmail = None
        task.metadata = None  # see api.thrift Metadata; will be displayed in the Aurora UI if set

        task.numCpus = jobrq['resources']['cpus']
        task.ramMb = jobrq['resources']['mem'] * sizes[jobrq['resources']['memunit']] / sizes['MB']
        task.diskMb = jobrq['resources']['disk'] * sizes[jobrq['resources']['diskunit']] / sizes['MB']

        task.job = key
        task.owner = owner
        task.requestedPorts = frozenset()
        task.taskLinks = {}
        task.constraints.add( Constraint(name=u'host', constraint=TaskConstraint(limit=LimitConstraint(limit=99999999), value=None)) )
        task.container = Container(docker=DockerContainer(image=jobrq['docker']), mesos=None)

        task.executorConfig = ExecutorConfig(
            name=AURORA_EXECUTOR_NAME,
            data=json.dumps(self._build_executor_config(jobid, jobrq, self.localize_cmd)))

        jobconf = JobConfiguration(
            key=key,
            owner=owner,
            cronSchedule=None,
            cronCollisionPolicy=CronCollisionPolicy.KILL_EXISTING,
            taskConfig=task,
            instanceCount=1)

        resp = self.client.createJob(jobconf)
        log.debug(resp)
