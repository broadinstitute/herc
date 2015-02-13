from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.web import RequestHandler, Application
from tornado import gen
from tornado import httpserver
import os.path
import subprocess
import json
from collections import OrderedDict
import time
import jsonvalidate
import aurora
import async
import inspect

class base(RequestHandler):
	def initialize(self):
		self.set_header( 'Content-Type', 'application/json' )
		self.set_header('Access-Control-Allow-Origin',	   '*')
		self.set_header('Access-Control-Allow-Credentials', 'true')

	def write_error(self, status_code, **kwargs):
		if self.settings.get("serve_traceback") and "exc_info" in kwargs:
			super(base, self).write_error(status_code, kwargs)
		else:
			self.set_header( 'Content-Type', 'application/json' )
			self.finish("%(code)d: %(message)s" % {
				"code": status_code,
				"message": self._reason
				})

class index(base):
	def get(self):
		"""Returns the list of endpoints that this webservice provides."""
		self.write( json.dumps(friendly_endpoints, indent=1) )
		self.finish()

class schema(base):
	def get(self):
		"""Returns the JSON schema used to validate job submission requests."""
		with open("data/schemas/jobsubmit.json", 'r') as jschema:
			self.write(jschema.read())
			self.finish()

class submit(base):
	@gen.coroutine
	def post(self):
		"""Submits a job request. Body must be JSON that validates against the JSON schema available at GET /schema. Returns a string, the job ID."""

		#Validate the request against the schema. This will raise an HTTPError if it fails validation.
		#jobrq = yield jsonvalidate.validate( self.request.body, "data/schemas/jobsubmit.json" )
		jobid = yield aurora.requestjob(None)

		#TODO:
		#1. DONE Validate the schema
		#2. Create the Aurora job config from the schema
		#3. Pass it off to the Aurora job create worker
		#4. Return "ok, it's been scheduled" (or an ID? do we create that?)

		# Aurora job create worker:
			# Might fail to create a job for some reason. In which case, return a "sry no" back on the job's ID
		self.write(jobid)
		self.finish()

class status(base):
	@gen.coroutine
	def get(self, jobid):
		"""Query Aurora and return the status of this job. 404 if not found, otherwise will return JSON with the job's current status and the time it entered that status."""
		status = yield aurora.status(jobid)
		self.write(json.dumps(status, indent=1))
		self.finish()

class sleep(base):
	@gen.coroutine
	def get(self, n = 0):
		"""Sleep for n seconds and then return."""
		ret = yield self.sleep( int(n) )
		self.write(ret)

	@async.usepool('long')
	def sleep(self, secs):
		then = time.time()
		time.sleep(secs)
		return "Slept for " + str(time.time()-then) + " seconds"

endpoints = {
	r'/' : {
		'class' : index,
		'friendly' : { 'get' : "/" }
	},
	r'/schema/?' : {
		'class' : schema,
		'friendly' : { 'get' : "/schema" }
	},
	r'/submit/?' : {
	'class' : submit,
	'friendly' : { 'post' : "/submit" }
	},
	r'/status/(.*)/?' : {
	'class' : status,
	'friendly' : { 'get' : "/status/jobid" }
	},
    r'/sleep/(.*)/?' : {
	'class' : sleep,
	'friendly' : { 'get' : "/sleep/n" }
	}
}

def prettify_endpoints():
	"""Turns the list of endpoints into an OrderedDict of friendlyname : description for use by /index."""
	http_methods = ['get', 'post', 'put', 'patch'] #others?

	# !!!
	# for each endpoint, get the methods of its associated RequestHandler class that are explicitly defined in this class and are in http_methods
	# from each of those methods, create a dictionary entry like { "METHOD /endpoint_friendly_name" : "(method's docstring)" }
	# they end up looking like { "GET /schema": "Returns the JSON schema used to validate job submission requests." }
	d =	{ mname.upper() + " " + endpoints[end]['friendly'][mname] : inspect.getdoc(meth)
	         for end in endpoints
	         for (mname, meth) in inspect.getmembers( endpoints[end]['class'], lambda m : inspect.ismethod(m)
	                                                                                      and m.__name__ in endpoints[end]['class'].__dict__
	                                                                                      and m.__name__ in http_methods ) }

	return OrderedDict( sorted(d.items(), key=lambda t: t[0]) )

#This used to be a one-liner in /index but it never changes, so why recalculate it
friendly_endpoints = prettify_endpoints()

def main():
	#Generate a self-signed certificate and key if we don't already have one.
	if not os.path.isfile("cert.pem") or not os.path.isfile("key.pem"):
		subprocess.call( 'openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 36500 -nodes -subj'.split() + ["/C=US/ST=MA/L=Cambridge/O=Broad Institute/OU=Prometheus"] )

	urls = [ (end, endpoints[end]['class']) for end in endpoints ]
	app = Application(urls, compress_response = True )
	ili=IOLoop.instance()
	async.io_loop=ili #set up io_loop for async executor
	http_server = httpserver.HTTPServer(app,
	                                    ssl_options={
	                                    "certfile": "cert.pem",
	                                    "keyfile": "key.pem"
	                                    },
	                                    io_loop=ili )
	http_server.listen(4372)

	#Trigger a callback that does nothing every half-second so KeyboardInterrupts can actually get through
	PeriodicCallback(lambda: None,500,ili).start()
	ili.start()
