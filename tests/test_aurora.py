from unittest import TestCase
import jinja_dicts
import webservice.aurora as aurora
import json

class TestAurora(TestCase):
	def test_build_jinjadict(self):
		"""Tests that we transform a JSON request into a Jinja template fill correctly."""
		with open('tests/data/full_submit.json', 'r') as fullsub:
			fullrq = json.load(fullsub)

		jinjadict = aurora.build_jinja_dict("TESTJOB", fullrq)
		self.assertEqual( jinjadict, jinja_dicts.full_submit )
