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

#States that Aurora considers terminal (but may end up rescheduled).
TERMINAL_STATES = ["LOST", "FINISHED", "FAILED", "KILLED"]

#If an Aurora job passes through one of these states, it will always be rescheduled.
RESCHEDULE_STATES = ["RESTARTING", "DRAINING", "PREEMPTING"]

#Additional state we add on top of Aurora's to indicate that a job is Aurora-terminal
#but will be cloned and rescheduled shortly.
RESCHEDULED_STATUS = "RESCHEDULED"

def determine_true_status(jobstatus):
	"""Aurora's definition of "terminal state" differs to ours.
	For instance, a job that gets LOST will typically get rescheduled.
	This function takes a job status object and avoids returning a terminal status if it'll be rescheduled."""
	status = jobstatus['status']
	statuslist = [ evt['status'] for evt in jobstatus['taskEvents'] ]
	if status not in TERMINAL_STATES:
		#Job is still in progress.
		return status
	elif any( [ x in RESCHEDULE_STATES for x in statuslist ] ):
		#Job is in a terminal state but will be rescheduled.
		#We should hit this rarely as the new task is created (and should therefore go active)
		#at the same time we transition from RESCHEDULE_STATES to TERMINAL_STATES
		return "RESCHEDULED"
	elif status == "LOST" and "KILLING" not in statuslist:
		#Job got lost during normal operation and will therefore be rescheduled.
		return "RESCHEDULED"
	elif "KILLING" in statuslist:
		#User requested this job was killed. It may actually have ended up in any of TERMINAL_STATES, but it
		#won't be rescheduled, so for simplicity we can hide this to users and pretend it was killed successfully.
		return "KILLED"
	else:
		#Job is terminal, wasn't killed, and won't be rescheduled. Report its status truthfully.
		return status


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

			#Sort inactive jobs in order of most recent submission time.
			#This catches the issue where a job gets rescheduled but the first run doesn't progress to a terminal state until after the second completes.
			jobruns = jobresult['active'] + sorted( jobresult['inactive'], key = lambda elem : elem['taskEvents'][0]['timestamp'], reverse = True )

			laststatus = jobruns[0]

			output['status'] = determine_true_status(laststatus)
			output['time'] = laststatus['taskEvents'][-1]['timestamp']
	else:
		output['status'] = 'FINISHED'
		output['time'] = int(time.time()*1000) #aurora returns unixtime ms so we should too

	return output
