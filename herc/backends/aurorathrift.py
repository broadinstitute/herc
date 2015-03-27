import getpass
import munch
from thrift.transport.THttpClient import THttpClient
from thrift.protocol.TJSONProtocol import TJSONProtocol
from gen.apache.aurora.api import AuroraSchedulerManager
from gen.apache.aurora.api.constants import AURORA_EXECUTOR_NAME, ACTIVE_STATES
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
                "disk": int(jobrq['resources']['disk'] * sizes[jobrq['resources']['diskunit']]),
                "ram" : int(jobrq['resources']['mem'] * sizes[jobrq['resources']['memunit']]),
                "cpu": float(jobrq['resources']['cpus'])
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
                            + [AuroraThrift._build_process(name = jobid + '_ps', cmd = jobrq['commandline'], final = False)] \
                            + uploads

        #order constraints of all processes so far - i.e. the non-final ones
        task['constraints'] = [ { "order" : [ p['name'] for p in task['processes'] ] } ]

        #finalizing processes to localize stdout and stderr up to gcs
        #these are guaranteed to run even if the task fails because one of the other processes fail.
        if jobrq['stdout'] != "":
            task['processes'].append(AuroraThrift._build_process(
                name = "__locup_stdout",
                cmd = localize_cmd + ' "' + config.get("aurora.sandboxdir") + '/.logs/' + jobid + '_ps/0/stdout" "' + jobrq['stdout'] + '"',
                final = True))
        if jobrq['stderr'] != "":
            task['processes'].append(AuroraThrift._build_process(
                name = "__locup_stderr",
                cmd = localize_cmd + ' "' + config.get("aurora.sandboxdir") + '/.logs/' + jobid + '_ps/0/stderr" "' + jobrq['stderr'] + '"',
                final = True))

        exconf['task'] = task
        return exconf

    @staticmethod
    def _build_job_config(jobid, jobrq, user, localize_cmd):
        """Builds the JobConfiguration Thrift object."""

        #The executorConfig is a JSON blob passed to the Task and on through to Thermos.
        #It contains most of the data that also goes into the JobConfiguration, so we'll
        #copy out the majority of the values from there to here in an attempt to keep
        #them in sync.
        exconf = munch.munchify(AuroraThrift._build_executor_config(jobid, jobrq, localize_cmd))

        owner = Identity(role=exconf.role, user=user)
        key = JobKey(
            role=exconf.role,
            environment=exconf.environment,
            name=exconf.name)

        task = TaskConfig()
        task.jobName = exconf.name
        task.environment = exconf.environment
        task.production = exconf.production
        task.isService = exconf.service
        task.maxTaskFailures = exconf.max_task_failures
        task.priority = exconf.priority
        task.contactEmail = None
        task.metadata = None  # see api.thrift Metadata; will be displayed in the Aurora UI if set

        task.numCpus = exconf.task.resources.cpu
        task.ramMb = int(exconf.task.resources.ram / sizes['MB'])
        task.diskMb = int(exconf.task.resources.disk / sizes['MB'])

        task.job = key
        task.owner = owner
        task.requestedPorts = frozenset()
        task.taskLinks = {}
        task.constraints = { Constraint(name='host', constraint=TaskConstraint(limit=LimitConstraint(limit=99999999), value=None)) }
        task.container = Container(docker=DockerContainer(image=exconf.container.docker.image), mesos=None)

        task.executorConfig = ExecutorConfig(
            name=AURORA_EXECUTOR_NAME,
            data=exconf.toJSON())

        return JobConfiguration(
            key=key,
            owner=owner,
            cronSchedule=None,
            cronCollisionPolicy=CronCollisionPolicy.KILL_EXISTING,
            taskConfig=task,
            instanceCount=1)

    def requestjob(self, jobid, jobrq):
        jobconf = AuroraThrift._build_job_config(jobid, jobrq, getpass.getuser(), self.localize_cmd)
        resp = self.client.createJob(jobconf, None, SessionKey(mechanism="UNAUTHENTICATED", data="UNAUTHENTICATED"))
        log.debug(resp)

    def status(self, jobid):
        jobkey = JobKey(role=config.get("aurora.cluster.role"),
                                    environment=config.get("aurora.cluster.env"),
                                    name=jobid)
        response = self.client.getTasksWithoutConfigs(TaskQuery(jobKeys=[jobkey]))
        job_tasks = response.result.scheduleStatusResult.tasks
        jobresult = self.get_status_for_job(jobkey, job_tasks)
        return jobresult

    def get_status_for_job(self, jobkey, job_tasks):
        """Make and return a job status object from a raw thrift response."""
        def is_active(task):
            return task.status in ACTIVE_STATES

        active_tasks = sorted([t for t in job_tasks if is_active(t)],
                            key=lambda task: task.assignedTask.instanceId)
        inactive_tasks = sorted([t for t in job_tasks if not is_active(t)],
                              key=lambda task: task.assignedTask.instanceId)
        result = [self.get_job_status_object(jobkey, active_tasks, inactive_tasks)]
        return result

    def get_job_status_object(self, jobkey, active_tasks, inactive_tasks):
        """Return an object containing info on the tasks running for a job."""
        def get_task_status_object(scheduled_task):
          """Return a single task object""" 
          task = scheduled_task
          # Now, clean it up: take all fields that are actually enums, and convert
          # their values to strings.
          task.status = ScheduleStatus._VALUES_TO_NAMES[task.status]
          events = sorted(task.taskEvents, key=lambda event: event.timestamp)
          for event in events:
            event.status = ScheduleStatus._VALUES_TO_NAMES[event.status]
          # convert boolean fields to boolean value names.
          assigned = task.assignedTask
          task_config = assigned.task
          task_config.isService = (task_config.isService != 0)
          return task

        return {"job": str(jobkey),
            "active": [get_task_status_object(task) for task in active_tasks],
            "inactive": [get_task_status_object(task) for task in inactive_tasks]}
