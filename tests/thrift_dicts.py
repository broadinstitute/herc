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
                "name": "locdown_0",
                "cmdline": 'localizer "gs://foo" "/foo"',
                "final": False, "daemon": False, "ephemeral": False,
                "max_failures": 1, "min_duration": 5
            },
            {
                "name": "locdown_1",
                "cmdline": 'localizer "boss://bar" "/bar"',
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
        "constraints" : [ { "order" : [ "locdown_0", "locdown_1", "TESTJOB_ps", "locup_0" ] } ]
    }
}
