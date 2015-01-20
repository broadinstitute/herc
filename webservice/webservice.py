from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.web import RequestHandler, Application
from tornado import httpserver
import os.path
import subprocess
import pprint

class base(RequestHandler):
	def initialize(self):
		self.set_header( 'Content-Type', 'application/json' )
		self.set_header('Access-Control-Allow-Origin',	   '*')
		self.set_header('Access-Control-Allow-Credentials', 'true')

class schema(base):
	def get(self):
		with open("data/schemas/jobsubmit.json", 'r') as schema:
			self.write(schema.read())
			self.finish()

class submit:
	def post(self):
		#TODO:
		#1. Validate the schema
		#2. Create the Aurora job config from the schema
		#3. Pass it off to the Aurora job create worker
		#4. Return "ok, it's been scheduled" (or an ID? do we create that?)

		# Aurora job create worker:
			# Might fail to create a job for some reason. In which case, return a "sry no" back on the job's ID
		pass

urls = [
	(r'/schema', schema)
]

def main():
	#Generate a self-signed certificate and key if we don't already have one.
	if not os.path.isfile("cert.pem") or not os.path.isfile("key.pem"):
		subprocess.call( 'openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 36500 -nodes -subj'.split() + ["/C=US/ST=MA/L=Cambridge/O=Broad Institute/OU=Prometheus"] )

	app = Application(urls, compress_response = True )
	ili=IOLoop.instance()
	http_server = httpserver.HTTPServer(app,
	                                    ssl_options={
	                                    "certfile": "cert.pem",
	                                    "keyfile": "key.pem"
	                                    },
	                                    io_loop=ili )
	http_server.listen(3333)

	#Trigger a callback that does nothing every half-second so KeyboardInterrupts can actually get through
	PeriodicCallback(lambda: None,500,ili).start()
	ili.start()
