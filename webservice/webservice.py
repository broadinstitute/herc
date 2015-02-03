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
		d = { end : endpoints[end]['desc'] for end in endpoints }
		self.write( json.dumps(OrderedDict(sorted(d.items(), key=lambda t: t[0])), indent=1) )
		self.finish()

class schema(base):
	def get(self):
		with open("data/schemas/jobsubmit.json", 'r') as schema:
			self.write(schema.read())
			self.finish()

class submit(base):
	@gen.coroutine
	def post(self):
		#Validate the request against the schema. This will raise an HTTPError if it fails validation.
		jobrq = yield jsonvalidate.validate( self.request.body, "data/schemas/jobsubmit.json" )
		yield aurora.requestjob(jobrq)

		#TODO:
		#1. DONE Validate the schema
		#2. Create the Aurora job config from the schema
		#3. Pass it off to the Aurora job create worker
		#4. Return "ok, it's been scheduled" (or an ID? do we create that?)

		# Aurora job create worker:
			# Might fail to create a job for some reason. In which case, return a "sry no" back on the job's ID
		self.write("success!")
		self.finish()

class sleep(base):
	@gen.coroutine
	def get(self):
		ret = yield self.sleep( int(self.get_query_argument('sleep', '0')) )
		self.write(ret)

	@async.usepool('shortjob')
	def sleep(self, secs):
		then = time.time()
		time.sleep(secs)
		return "Slept for " + str(time.time()-then) + " seconds"

endpoints = {
	r'/' : {
		'class' : index,
	    'desc' : "This page."
	},
	r'/schema' : {
		'class' : schema,
	    'desc' : "Returns the JSON used to validate job submission requests."
	},
	r'/submit' : {
	'class' : submit,
	'desc' : "POST your job request here."
	},
    r'/sleep' : {
	'class' : sleep,
	'desc' : "GET?sleep=n to sleep for n seconds and then return."
	}
}

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
