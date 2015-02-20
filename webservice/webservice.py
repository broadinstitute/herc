from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.web import RequestHandler, Application
from tornado import gen
from tornado import httpserver
import os.path
import subprocess
import json
import time
import jsonvalidate
import aurora
import async
import endpoints
import ssl

class base(RequestHandler):
	def initialize(self):
		self.set_header( 'Content-Type', 'application/json' )
		self.set_header('Access-Control-Allow-Origin',	   '*')
		self.set_header('Access-Control-Allow-Credentials', 'true')

	def write_error(self, status_code, **kwargs):
		if self.settings.get("serve_traceback") and "exc_info" in kwargs:
			super(base, self).write_error(status_code, kwargs)
		else:
			log_msg = None
			try:
				log_msg = kwargs['exc_info'][1].log_message
			except (KeyError, AttributeError):
				pass
			finally:
				log_msg = self._reason if log_msg is None else log_msg

			self.set_header( 'Content-Type', 'application/json' )
			self.finish("%(code)d: %(message)s" % {
				"code": status_code,
				"message": log_msg
				})

class index(base):
	def get(self):
		"""GET /
		Returns the list of endpoints that this webservice provides."""
		self.write( json.dumps(pretty_endpoints, indent=1) )
		self.finish()

class schema(base):
	def get(self):
		"""GET /schema
		Returns the JSON schema used to validate job submission requests."""
		with open("data/schemas/jobsubmit.json", 'r') as jschema:
			self.write(jschema.read())
			self.finish()

class submit(base):
	@gen.coroutine
	def post(self):
		"""POST /submit
		Submits a job request. Body must be JSON that validates against the JSON schema available at GET /schema. Returns a string, the job ID."""

		#Validate the request against the schema, filling in defaults. This will raise an HTTPError if it fails validation.
		jobrq = yield jsonvalidate.validate( self.request.body, "data/schemas/jobsubmit.json" )
		jobid = yield aurora.requestjob(jobrq)

		self.write(jobid)
		self.finish()

class status(base):
	@gen.coroutine
	def get(self, jobid):
		"""GET /status/<jobid>
		Query Aurora and return the status of this job. 404 if not found, otherwise will return JSON with the job's current status and the time it entered that status."""
		status = yield aurora.status(jobid)
		self.write(json.dumps(status, indent=1))
		self.finish()

class sleep(base):
	@gen.coroutine
	def get(self, n = 0):
		"""GET /sleep/<n>
		Sleep for n seconds and then return."""
		ret = yield self.sleep( int(n) )
		self.write(ret)

	@async.usepool('long')
	def sleep(self, secs):
		then = time.time()
		time.sleep(secs)
		return "Slept for " + str(time.time()-then) + " seconds"

endpoint_mapping = {
	r'/' : { 'class' : index },
	r'/schema/?' : { 'class' : schema },
	r'/submit/?' : { 'class' : submit },
	r'/status/(.*)/?' : { 'class' : status },
    r'/sleep/(.*)/?' : { 'class' : sleep }
}
pretty_endpoints = endpoints.prettify(endpoint_mapping)

def main():
	#Generate a self-signed certificate and key if we don't already have one.
	if not os.path.isfile("herc.crt") or not os.path.isfile("herc.key"):
		subprocess.call( 'openssl req -x509 -newkey rsa:2048 -keyout herc.key -out herc.crt -days 36500 -nodes -subj'.split() + ["/C=US/ST=MA/L=Cambridge/O=Broad Institute/OU=Prometheus"] )

	urls = [ (end, endpoint_mapping[end]['class']) for end in endpoint_mapping ]
	app = Application(urls, compress_response = True )
	ili=IOLoop.instance()
	async.io_loop=ili #set up io_loop for async executor

	http_server = httpserver.HTTPServer(app,
	                                    ssl_options={
	                                    "certfile": "herc.crt",
	                                    "keyfile": "herc.key"	                                    },
	                                    io_loop=ili )
	http_server.listen(4372)

	#Trigger a callback that does nothing every half-second so KeyboardInterrupts can actually get through
	PeriodicCallback(lambda: None,500,ili).start()
	ili.start()
