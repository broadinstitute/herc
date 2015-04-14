from gen.apache.aurora.api.ttypes import *
from gen.apache.aurora.api.constants import AURORA_EXECUTOR_NAME
import munch

exconf = {
    "environment" : "devel",
    "container" : { 'docker' : { 'image' : "python:2.7" } },
    "name" : "TESTJOB",
    "service" : False,
    "max_task_failures" : 1,
    "cron_collision_policy" : "KILL_EXISTING",
    "priority": 0,
    "cluster": "herc",
    "health_check_config": {
        "initial_interval_secs": 15,
        "interval_secs": 10,
        "timeout_secs": 1,
        "max_consecutive_failures": 0
    },
    "role": "test",
    "enable_hooks": False,
    "production": False,
    "constraints": { "host": "limit:99999999" },

    "task" : {
        "name": 'TESTJOB_task',
        "finalization_wait": 30,
        "max_failures": 1,
        "max_concurrency": 0,
        "resources": {
            "disk": 1*1024*1024,
            "ram" : 16*1024*1024,
            "cpu": 1.0
        },
        "processes": [
            {
                "name": "mkdir",
                "cmdline": 'mkdir -p /mnt/mesos/sandbox/sandbox/__jobio/input /mnt/mesos/sandbox/sandbox/__jobio/output',
                "final": False, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            },
            {
                "name": "symlink_in",
                "cmdline": 'ln -s /mnt/mesos/sandbox/sandbox/__jobio/input /job/input',
                "final": False, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            },
            {
                "name": "symlink_out",
                "cmdline": 'ln -s /mnt/mesos/sandbox/sandbox/__jobio/output /job/output',
                "final": False, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            },
            {
                "name": "locdown_0",
                "cmdline": 'localizer "gs://foo" "/foo"',
                "final": False, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            },
            {
                "name": "locdown_1",
                "cmdline": 'localizer "http://bar" "/bar"',
                "final": False, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            },
            {
                "name": "TESTJOB_ps",
                "cmdline": 'echo Hello herc! > /baz',
                "final": False, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            },
            {
                "name": "locup_0",
                "cmdline": 'localizer "/baz" "gs://baz"',
                "final": False, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            },
            {
                "name": "__locup_stdout",
                "cmdline": 'localizer "/mnt/mesos/sandbox/sandbox/.logs/TESTJOB_ps/0/stdout" "gs://stdout"',
                "final": True, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            },
            {
                "name": "__locup_stderr",
                "cmdline": 'localizer "/mnt/mesos/sandbox/sandbox/.logs/TESTJOB_ps/0/stderr" "gs://stderr"',
                "final": True, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            }
        ],
        "constraints" : [ { "order" : [ "mkdir", "symlink_in", "symlink_out", "locdown_0", "locdown_1", "TESTJOB_ps", "locup_0" ] } ]
    }
}

_key=JobKey(role="test",
                environment="devel",
                name="TESTJOB")
_owner=Identity(role="test", user="test")

jobconf = JobConfiguration(
            key=_key,
            owner=_owner,
            cronSchedule=None,
            cronCollisionPolicy=CronCollisionPolicy.KILL_EXISTING,
            taskConfig=TaskConfig(
                jobName="TESTJOB",
                environment="devel",
                production=False,
                isService=False,
                maxTaskFailures=1,
                priority=0,
                contactEmail=None,
                metadata=None,
                numCpus=1.0,
                ramMb=16,
                diskMb=1,
                job=_key,
                owner=_owner,
                requestedPorts=frozenset(),
                taskLinks={},
                constraints=set([ Constraint(name=u'host', constraint=TaskConstraint(limit=LimitConstraint(limit=99999999), value=None)) ]),
                container=Container(docker=DockerContainer(image='python:2.7'), mesos=None),
                executorConfig=ExecutorConfig(
                    name=AURORA_EXECUTOR_NAME,
                    data=munch.munchify(exconf).toJSON()
                )
            ),
            instanceCount=1)
