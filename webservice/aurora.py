from jinja2 import FileSystemLoader
from jinja2 import Environment
import async
import tempfile
import uuid
import subprocess
import os
import time

loader = FileSystemLoader('jobdefs')
env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)

@async.usepool('longps')
def requestjob(jobrq):
	"""Takes the job request object and converts it into an Aurora definition file.
	Creates a GUID and submits the Aurora definition file to Aurora with the GUID.
	"""

	jobid = "job_" + str(uuid.uuid4()).replace('-', '_')

	jr = dict()

	#processes list made of command lines
	#the final version of this is probably going to look something like:
	# 1. foreach input in jobrq['inputs']: download_from_gcs.py input inputs[input]
	# 2. run a command line
	# 3. foreach output in jobrq['outputs']: upload_to_gcs.py output outputs[output]
	jr['processes'] = [ { 'name' : 'foo_ps', 'cmd' : 'echo bar' } ]

	#construct the task list in order, such that the last task is the (single) task to run from the job.
	#there's currently no space in the template to do Tasks.combine() or Tasks.concat().
	jr['tasks'] = [ {   'name' : 'foo_task',
	                    'type' : 'SequentialTask',
	                    'processes' : map( lambda p : p['name'], jr['processes'] ),
	                    'cpus' : 1,
	                    'mem'  : 1,
	                    'memunit' : "GB",
	                    'disk' : 2,
	                    'diskunit' : "MB"
	                } ]

	#as above: we assume the tasks list has been constructed such that the last task
	#in the list is the one we want to execute for this job.
	jr['jobs'] = [ {    'name' : jobid,
	                    'task' : jr['tasks'][-1]['name'],
						'env'  : 'devel',   #configurable?
	                    'cluster' : 'herc', #also configurable?
	                    'hostlimit' : 99999999
	                    #instance and docker configuration both go here, someday
					} ]

	template = env.get_template('jobtemplate.aurora')

	tmpfile = tempfile.NamedTemporaryFile(suffix=".aurora")

	#might error.
	tmpfile.write( template.render(jr) )
	tmpfile.flush()
	os.fsync(tmpfile.fileno())

	#what does aurora return here?
	#we could parse the output...
	then = time.time()
	subprocess.call( ['aurora', 'job', 'create', 'herc/jclouds/devel/' + jobid, tmpfile.name] )
	auroratime = time.time() - then

	#don't do this until after the job is submitted
	tmpfile.close()

	return jobid
