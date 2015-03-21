from unittest import TestCase
from herc.backends import AuroraThrift
import tests.thrift_dicts as thrift_dicts
import json
import mock

fake_config = {
    "aurora.cluster.env" : "devel",
    "aurora.cluster.name" : "herc",
    "aurora.cluster.role" : "test",
    "aurora.sandboxdir" : "/mnt/mesos/sandbox/sandbox"
}

class TestAuroraThrift(TestCase):
    maxDiff = None
    def test_build_executor_config(self):
        with open('tests/data/full_submit.json', 'r', encoding="utf-8") as fullsub:
            fullrq = json.load(fullsub)

            with mock.patch('herc.config.get') as config:
                config.side_effect = lambda val : fake_config[val]
                exconf = AuroraThrift._build_executor_config("TESTJOB", fullrq, "localizer")
                self.assertEqual( exconf, thrift_dicts.exconf )

    def test_build_job_config(self):
        with open('tests/data/full_submit.json', 'r', encoding="utf-8") as fullsub:
            fullrq = json.load(fullsub)

            with mock.patch('herc.config.get') as config:
                config.side_effect = lambda val : fake_config[val]
                jobconf = AuroraThrift._build_job_config("TESTJOB", fullrq, "test", "localizer")
                self.assertEqual( jobconf, thrift_dicts.jobconf )
