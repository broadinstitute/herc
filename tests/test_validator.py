import tornado.testing
from tornado.web import HTTPError
import herc.jsonvalidate as jsonvalidate
import json

def get_str(path):
	with open(path, 'r', encoding="utf-8") as fullfile:
		content = fullfile.read()
		return content

class TestValidator(tornado.testing.AsyncTestCase):

	@tornado.testing.gen_test
	def test_validate_fullrq(self):
		"""Tests that a correct, full submission request validates."""
		fullrq = get_str('tests/data/full_submit.json')

		validated = yield jsonvalidate.validate( fullrq, "data/schemas/jobsubmit.json" )
		self.assertEqual( validated, json.loads(fullrq) )

	@tornado.testing.gen_test
	def test_validate_partialrq(self):
		"""Tests that a correct, partial submission request validates, and is returned with missing data supplied."""
		partialrq = get_str('tests/data/partial_submit.json')
		fullrq = get_str('tests/data/default_submit.json')

		validated = yield jsonvalidate.validate( partialrq, "data/schemas/jobsubmit.json" )
		self.assertEqual( validated, json.loads(fullrq), "json returned from jsonvalidate should have defaults filled in" )

	@tornado.testing.gen_test
	def test_validate_nonsenserq(self):
		"""Test that nonsense not-JSON fails to validate and returns an error."""
		with self.assertRaises(HTTPError) as httpe:
			yield jsonvalidate.validate("&&23908fff__fff", "data/schemas/jobsubmit.json")
		self.assertEqual(httpe.exception.status_code, 400)
