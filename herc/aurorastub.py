

class AuroraStub(object):
    """Mock Aurora backend that returns correct-looking data."""

    def __init__(self):
        pass

    def requestjob(self, jobid, jobrq):
        """No return value required; nothing to do."""
        return None

    def status(self, jobid):
        """Returns a good-looking placeholder job status."""
        with open("data/stub_aurora_jobstatus.json", 'r') as fakestatus:
            return fakestatus.read()
