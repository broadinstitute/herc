from jinja2 import FileSystemLoader
from jinja2 import Environment
import async
import tempfile
import uuid
import subprocess
import os
import time
import json
from tornado.web import HTTPError

loader = FileSystemLoader('jobdefs')
env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)

aurora_checked = False
aurora_exists = True
def _aurora_installed():
	global aurora_checked
	global aurora_exists

	if not aurora_checked:
		aurora_checked = True
		try:
			subprocess.call(["aurora"])
			aurora_exists = True
		except OSError:
			print "WARNING: aurora not installed, aurora endpoints will return dummy values"
			aurora_exists = False
	return aurora_exists

@async.usepool('aurora')
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
	if _aurora_installed():
		then = time.time()
		subprocess.call( ['aurora', 'job', 'create', 'herc/jclouds/devel/' + jobid, tmpfile.name] )
		auroratime = time.time() - then

	#don't do this until after the job is submitted
	tmpfile.close()

	return jobid

@async.usepool('aurora')
def status(jobid):
	"""Return the status of this job ID on Aurora.
	See the Aurora code for a full list of statuses:
		https://github.com/apache/incubator-aurora/blob/61e6c35f91e959ba6247dddc3fe3524795c5f851/api/src/main/thrift/org/apache/aurora/gen/api.thrift#L348
	"""
	output = dict()
	output['jobid'] = jobid

	if _aurora_installed():
		then = time.time()
		resjson = subprocess.check_output( ['aurora', 'job', 'status', 'herc/jclouds/devel/' + jobid, "--write-json"] )
		auroratime = time.time() - then

		jobresult = json.loads(resjson)
		if 'error' in jobresult:
			# {"jobspec":"herc/jclouds/devel/nonexistent_job","error":"No matching jobs found"}
			raise HTTPError(404, "Job ID " + jobid + " not found")
		else:
			# example json is in data/example_aurora_jobstatus.json
			jobresult = jobresult[0]

			#Assuming unique IDs per job, the length of these two arrays will usually sum to 1.
			#However, Aurora will retry LOST jobs, and may kill and reschedule jobs for host maintenance or job pre-emption.
			#See https://broadinstitute.atlassian.net/browse/DSDEES-21
			jobruns = jobresult['active'] + jobresult['inactive']

			lastrun = jobruns[0]

			output['status'] = lastrun['status']
			output['time'] = lastrun['taskEvents'][-1]['timestamp']
	else:
		output['status'] = 'FINISHED'
		output['time'] = int(time.time()*1000) #aurora returns unixtime ms so we should too

	return output
