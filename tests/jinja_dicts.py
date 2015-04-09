full_submit = {
	'processes' : [
        { 'name' : "__symlink_twiddle", 'cmd' : 'mkdir "/mnt/mesos/sandbox/sandbox/__jobio"; ln -s "/mnt/mesos/sandbox/sandbox/__jobio" "/job"' },
		{ 'name' : "locdown_0", 'cmd' : 'localizer "gs://foo" "/foo"' },
		{ 'name' : "locdown_1", 'cmd' : 'localizer "http://bar" "/bar"' },
		{ 'name' : "TESTJOB_ps", 'cmd' : 'echo Hello herc! > /baz' },
		{ 'name' : "locup_0", 'cmd' : 'localizer "/baz" "gs://baz"' }
	],
    'finalizers' : [
        { 'name' : "__locup_stdout", 'cmd' : 'localizer ".logs/TESTJOB_ps/0/stdout" "gs://stdout"' },
        { 'name' : "__locup_stderr", 'cmd' : 'localizer ".logs/TESTJOB_ps/0/stderr" "gs://stderr"' }
    ],
    'tasks' : [{    'name' : 'TESTJOB_task',
                    'processes' : [ "__symlink_twiddle", "locdown_0", "locdown_1", "TESTJOB_ps", "locup_0", "__locup_stdout", "__locup_stderr" ],
                    'ordering' : [ "__symlink_twiddle", "locdown_0", "locdown_1", "TESTJOB_ps", "locup_0" ],
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
