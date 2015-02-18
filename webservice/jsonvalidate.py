import async
import jsonref
import jsonschema
from tornado.web import HTTPError

#Lifted from https://python-jsonschema.readthedocs.org/en/latest/faq/
def extend_with_default(validator_class):
	validate_properties = validator_class.VALIDATORS["properties"]

	def set_defaults(validator, properties, instance, schema):
		for error in validate_properties( validator, properties, instance, schema ):
			yield error

		for property, subschema in properties.iteritems():
			if "default" in subschema:
				instance.setdefault(property, subschema["default"])

	return jsonschema.validators.extend( validator_class, {"properties" : set_defaults} )

validator_fill_defaults = extend_with_default(jsonschema.Draft4Validator)

@async.usepool('short')
def validate(jsonstr, schemapath):
	"""Take a string, load it into JSON, and validate it against the given schema.
	Returns the validated Python dict if it validates; otherwises, raises 400 Bad Request."""

	#Attempt to load the schema first
	try:
		with open(schemapath, 'r') as schemaf:
			schema = jsonref.load(schemaf)
	except ValueError:
		raise HTTPError(500, "Something appears to be wrong with the Aurora job schema! This is definitely a bug.")

	#Now validate the schema given.
	try:
		submitrq = jsonref.loads(jsonstr)
		validator_fill_defaults(schema).validate(submitrq)
		return submitrq

	except TypeError:
		raise HTTPError(400, "Not a valid JSON object.")
	except ValueError:
		raise HTTPError(400, "Not a valid JSON object.")
	except jsonschema.ValidationError:
		raise HTTPError(400, "Not a valid Aurora job submission request. Job submissions should conform to the JSON schema available at the /schema endpoint.")
	except jsonschema.SchemaError:
		raise HTTPError(500, "Something appears to be wrong with the Aurora job schema! This is definitely a bug.")
