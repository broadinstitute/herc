import async
import json
import jsonschema
from tornado.web import HTTPError

@async.usepool('shortjob')
def validate(str, schemapath):
	"""Take a string, load it into JSON, and validate it against the given schema.
	Returns the validated Python dict if it validates; otherwises, raises 400 Bad Request."""

	#Attempt to load the schema first
	try:
		with open(schemapath, 'r') as schemaf:
			schema = json.load(schemaf)
	except ValueError:
		raise HTTPError(500, "Something appears to be wrong with the Aurora job schema! This is definitely a bug.")

	#Now validate the schema given.
	try:
		submitrq = json.loads(str)
		jsonschema.validate(submitrq, schema)
	except TypeError:
		raise HTTPError(400, "Not a valid JSON object.")
	except ValueError:
		raise HTTPError(400, "Not a valid JSON object.")
	except jsonschema.ValidationError:
		raise HTTPError(400, "Not a valid Aurora job submission request. Job submissions should conform to the JSON schema available at the /schema endpoint.")
	except jsonschema.SchemaError:
		raise HTTPError(500, "Something appears to be wrong with the Aurora job schema! This is definitely a bug.")
