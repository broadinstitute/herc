import json
import munch

class AuroraMock(object):
    """Mock Aurora backend that returns correct-looking data."""

    def __init__(self, fakestatuspath = "data/stub_aurora_jobstatus.json"):
        self.fakestatuspath = fakestatuspath

    def requestjob(self, jobid, jobrq, vault_api_token):
        """No return value required; nothing to do."""
        return None

    def status(self, jobid):
        """Returns a good-looking placeholder job status."""
        with open(self.fakestatuspath, 'r', encoding='utf-8') as fakestatus:
            statusstring = fakestatus.read()
            statusjson = json.loads(statusstring)
            munchifiedstatus = munch.munchify(statusjson)
            return munchifiedstatus
