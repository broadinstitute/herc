from unittest import TestCase
import jinja_dicts
import webservice.aurora as aurora
import json

class TestAurora(TestCase):
	def test_build_jinjadict(self):
		"""Test that we transform a JSON request into a Jinja template fill correctly."""
		with open('tests/data/full_submit.json', 'r') as fullsub:
			fullrq = json.load(fullsub)

		jinjadict = aurora.build_jinja_dict("TESTJOB", fullrq)
		self.assertEqual( jinjadict, jinja_dicts.full_submit )

	def build_mock_jobstatus(self, statuses):
		"""Builds a minimal, mock jobstatus from the list of statuses."""
		st = dict()
		st['status'] = statuses[-1]
		st['taskEvents'] = [ { 'status' : status, 'timestamp' : idx } for (idx, status) in enumerate(statuses) ]
		return st

	def test_nonterm_status(self):
		"""Test that we correctly report nonterminal statuses."""
		nonterm_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "RUNNING" ])
		self.assertEqual( aurora.determine_true_status(nonterm_status), "RUNNING" )

	def test_lost_status(self):
		"""Test that we report lost jobs as rescheduled if they didn't get killed."""
		lost_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "LOST" ])
		self.assertEqual( aurora.determine_true_status(lost_status), "RESCHEDULED" )

	def test_killed_status(self):
		"""Test that we report user killed jobs as killed."""
		killed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "KILLING", "KILLED" ])
		self.assertEqual( aurora.determine_true_status(killed_status), "KILLED" )

	def test_lost_killed_status(self):
		"""Test that we report user killed jobs as killed, even if they get lost."""
		lost_killed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "KILLING", "LOST" ])
		self.assertEqual( aurora.determine_true_status(lost_killed_status), "KILLED" )

	def test_kill_failed_status(self):
		"""Test that we report user killed jobs as killed, even if they complete before the kill request gets through."""
		#NOTE: According to the Aurora state machine, it's possible for a user to request a job be killed, but it
		#finishes or fails before the kill request arrives. In this case, it proceeds to finished or failed.
		#For simplicity, we tell users that the job was successfully killed, even if it did something else.
		kill_failed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "KILLING", "FAILED" ])
		self.assertEqual( aurora.determine_true_status(kill_failed_status), "KILLED" )

	def test_preempting_status(self):
		"""Test that we report PREEMPTING -> KILLED jobs as rescheduled."""
		preempting_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "PREEMPTING", "KILLED" ])
		self.assertEqual( aurora.determine_true_status(preempting_status), "RESCHEDULED" )

	def test_restarting_status(self):
		"""Test that we report RESTARTING -> KILLED jobs as rescheduled."""
		restarting_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "RESTARTING", "KILLED" ])
		self.assertEqual( aurora.determine_true_status(restarting_status), "RESCHEDULED" )

	def test_failed_status(self):
		"""Test that we report terminal failed jobs as such."""
		failed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "RUNNING", "FAILED" ])
		self.assertEqual( aurora.determine_true_status(failed_status), "FAILED" )
