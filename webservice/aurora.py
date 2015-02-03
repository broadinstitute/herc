from tornado.web import HTTPError
import async

@async.usepool('longps')
def requestjob(jobrq):
	"""Takes the job request object and converts it into an Aurora definition file.
	Creates a GUID and submits the Aurora definition file to Aurora with the GUID.
	"""
	pass
