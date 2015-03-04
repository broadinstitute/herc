import herc.aurorasched as scheduler
import herc.aurorastub as aurorastub
import mock
import tornado.testing
from tornado.testing import gen_test

class TestScheduler(tornado.testing.AsyncTestCase):
    def build_mock_jobstatus(self, statuses, failmsg = "PLACEHOLDER: Job failed."):
        """Builds a minimal, mock jobstatus from the list of statuses."""
        st = dict()
        st['status'] = statuses[-1]
        st['taskEvents'] = [ { 'status' : status, 'timestamp' : idx, 'message' : failmsg if status == "FAILED" else "" } for (idx, status) in enumerate(statuses) ]
        return st

    def test_nonterm_status(self):
        """Test that we correctly report nonterminal statuses."""
        nonterm_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "RUNNING" ])
        self.assertEqual( scheduler.determine_true_status(nonterm_status)[0], "RUNNING" )

    def test_lost_status(self):
        """Test that we report lost jobs as rescheduled if they didn't get killed."""
        lost_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "LOST" ])
        self.assertEqual( scheduler.determine_true_status(lost_status)[0], "RESCHEDULED" )

    def test_killed_status(self):
        """Test that we report user killed jobs as killed."""
        killed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "KILLING", "KILLED" ])
        self.assertEqual( scheduler.determine_true_status(killed_status)[0], "KILLED" )

    def test_lost_killed_status(self):
        """Test that we report user killed jobs as killed, even if they get lost."""
        lost_killed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "KILLING", "LOST" ])
        self.assertEqual( scheduler.determine_true_status(lost_killed_status)[0], "KILLED" )

    def test_kill_failed_status(self):
        """Test that we report user killed jobs as killed, even if they complete before the kill request gets through."""
        #NOTE: According to the Aurora state machine, it's possible for a user to request a job be killed, but it
        #finishes or fails before the kill request arrives. In this case, it proceeds to finished or failed.
        #For simplicity, we tell users that the job was successfully killed, even if it did something else.
        kill_failed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "KILLING", "FAILED" ])
        self.assertEqual( scheduler.determine_true_status(kill_failed_status)[0], "KILLED" )

    def test_preempting_status(self):
        """Test that we report PREEMPTING -> KILLED jobs as rescheduled."""
        preempting_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "PREEMPTING", "KILLED" ])
        self.assertEqual( scheduler.determine_true_status(preempting_status)[0], "RESCHEDULED" )

    def test_restarting_status(self):
        """Test that we report RESTARTING -> KILLED jobs as rescheduled."""
        restarting_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "RESTARTING", "KILLED" ])
        self.assertEqual( scheduler.determine_true_status(restarting_status)[0], "RESCHEDULED" )

    def test_failed_status(self):
        """Test that we report terminal failed jobs as such."""
        failed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "RUNNING", "FAILED" ])
        self.assertEqual( scheduler.determine_true_status(failed_status)[0], "FAILED" )

    def test_mem_exceeded(self):
        """Test that we report memory exceeded jobs as such, and correctly pull out requested and used limits"""
        failed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "RUNNING", "FAILED" ],
                                                  failmsg = "Memory limit exceeded: Requested 128MB, Used 130MB." )
        aurora_status = scheduler.determine_true_status(failed_status)
        self.assertEqual( aurora_status[0], "MEM_EXCEEDED" )
        self.assertEqual( aurora_status[1]['requested'], "128MB" )
        self.assertEqual( aurora_status[1]['used'], "130MB" )

    def test_disk_exceeded(self):
        """Test that we report disk exceeded jobs as such, and correctly pull out requested and used limits"""
        failed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "RUNNING", "FAILED" ],
                                                  failmsg = "Disk limit exceeded.  Reserved 1234 bytes vs used 2345 bytes." )
        aurora_status = scheduler.determine_true_status(failed_status)
        self.assertEqual( aurora_status[0], "DISK_EXCEEDED" )
        self.assertEqual( aurora_status[1]['requested'], "1234BYTES" )
        self.assertEqual( aurora_status[1]['used'], "2345BYTES" )

    def test_unexpected_overlimit_string(self):
        """Test that we correctly assert if the overlimit string is unexpected."""
        failed_status = self.build_mock_jobstatus([ "INIT", "PENDING", "ASSIGNED", "RUNNING", "FAILED" ],
                                                  failmsg = "Memory limit exceeded: asked for 128MB, spent 130MB." )
        with self.assertRaises(AssertionError):
            scheduler.determine_true_status(failed_status)

    @tornado.testing.gen_test #required because scheduler.status uses @async.usepool
    def test_handle_interleaved_jobcompletion(self):
        """Test that job retries finishing in strange orders return a consistent order."""
        with mock.patch('herc.aurorasched.get_backend') as asc_get_backend:
            #submit times are ascending, but completion times are descending
            asc_get_backend.return_value = aurorastub.AuroraStub("tests/data/jobstatus_ascending_submittimes.json")
            status = yield scheduler.status("sample")
            self.assertEqual( status['status'], "FINISHED")

        with mock.patch('herc.aurorasched.get_backend') as desc_get_backend:
            #submit times are descending, but completion times are ascending
            desc_get_backend.return_value = aurorastub.AuroraStub("tests/data/jobstatus_descending_submittimes.json")
            status = yield scheduler.status("sample")
            self.assertEqual( status['status'], "FINISHED")
