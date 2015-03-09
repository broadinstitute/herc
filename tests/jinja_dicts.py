full_submit = {
	'processes' : [
		{ 'name' : "locdown_0", 'cmd' : 'localizer "gs://foo" "/foo"' },
		{ 'name' : "locdown_1", 'cmd' : 'localizer "boss://bar" "/bar"' },
		{ 'name' : "TESTJOB_ps", 'cmd' : 'echo Hello herc! > /baz' },
		{ 'name' : "locup_0", 'cmd' : 'localizer "/baz" "gs://baz"' }
	],
    'tasks' : [{    'name' : 'TESTJOB_task',
                    'type' : 'SequentialTask',
                    'processes' : [ "locdown_0", "locdown_1", "TESTJOB_ps", "locup_0" ],
                    'cpus' : 1,
                    'mem'  : 16,
                    'memunit' : "MB",
                    'disk' : 1,
                    'diskunit' : "MB"
    }],
    'jobs' : [{ 'name' : 'TESTJOB',
                'task' : 'TESTJOB_task',
                'env'  : 'devel',
                'cluster' : 'herc',
                'hostlimit' : 99999999,
                'container' : "python:2.7"
    }]
}
