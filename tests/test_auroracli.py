from unittest import TestCase
import tests.jinja_dicts as jinja_dicts
from herc.backends import AuroraCLI
import json

class TestAuroraCLI(TestCase):
    def test_build_jinjadict(self):
        """Test that we transform a JSON request into a Jinja template fill correctly."""
        with open('tests/data/full_submit.json', 'r', encoding="utf-8") as fullsub:
            fullrq = json.load(fullsub)

        jinjadict = AuroraCLI._build_jinja_dict("TESTJOB", fullrq, "localizer")
        self.assertEqual( jinjadict, jinja_dicts.full_submit )

        # TODO: Test that jinja correctly renders an .aurora file out of the jinjadict

# TODO: test config loading?
# TODO: test backend fallback mechanism?
# TODO: test webservice endpoints give 200s / 404s / 400s as expected (given mock everythings)?
