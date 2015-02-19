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
	"""Utility method so we can return stub results for an installation of Herc that's not actually connected to Aurora."""
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

def build_jinja_dict(jobid, jobrq):
	"""Takes an ID and job request object and converts it into a Python object for passing to Jinja."""

	#the job request we're going to fill in
	jr = dict()

	#processes to localize down from the "inputs" part of the schema
	downloads = [ { 'name' : "locdown_"+str(idx),
	                'cmd'  : 'echo localize "' + path['cloud'] + '" "' + path['local'] + '">>localize' }
	              for (idx, path) in enumerate(jobrq['inputs']) ]

	#processes to localize back up to the cloud from the "outputs" part of the schema
	uploads = [ { 'name' : "locup_"+str(idx),
	              'cmd'  : 'echo localize "' + path['local'] + '" "' + path['cloud'] + '">>localize' }
	            for (idx, path) in enumerate(jobrq['outputs']) ]

	#list of processes: download, run the commandline, upload
	jr['processes'] = downloads + [{ 'name' : jobid +'_ps', 'cmd' : jobrq['commandline'] }] + uploads

	#Currently all we need is one task, made of the list of download + run + upload processes.
	#We don't (yet?) need to do anything clever with Tasks.concat() or combine(), and the template doesn't support it.
	#The last task in this list will be used as the task to run on the job, so if we ever do use Tasks.concat() or
	#combine(), that should be the final task in this list.
	jr['tasks'] = [ {   'name' : jobid+'_task',
	                    'type' : 'SequentialTask',
	                    'processes' : map( lambda p : p['name'], jr['processes'] ),
	                    'cpus' : jobrq['resources']['cpus'],
	                    'mem'  : jobrq['resources']['mem'],
	                    'memunit' : jobrq['resources']['memunit'],
	                    'disk' : jobrq['resources']['disk'],
	                    'diskunit' : jobrq['resources']['diskunit']
	                } ]

	#as above: we assume the tasks list has been constructed such that the last task
	#in the list is the one we want to execute for this job.
	jr['jobs'] = [ {    'name' : jobid,
	                    'task' : jr['tasks'][-1]['name'],
	                    'env'  : 'devel',   #configurable?
	                    'cluster' : 'herc', #also configurable?
	                    'hostlimit' : 99999999,
	                    'container' : jobrq['docker']
	                    #instance configuration goes here, if we ever use it
	               } ]

	return jr

@async.usepool('aurora')
def requestjob(jobrq):
	"""Takes the job request object and converts it into an Aurora definition file.
	Creates a GUID and submits the Aurora definition file to Aurora with the GUID.
	"""

	#create a GUID for this job.
	jobid = "job_" + str(uuid.uuid4()).replace('-', '_')

	jr = build_jinja_dict(jobid, jobrq)

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

	print template.render(jr)

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
