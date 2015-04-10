import shortuuid
import json
import re
import random
from tornado.web import HTTPError
import threading
import importlib
from . import async
from . import config
from . import backends


def _importclass(classpath):
    """Turns a string representing a Python class into the actual class object.
    May return ImportError or AttributeError if you do something that's not legit."""
    path = classpath.rsplit( ".", 1 )

    # load the module, will raise ImportError if module cannot be loaded
    m = importlib.import_module(path[0])

    # get the class, will raise AttributeError if class cannot be found
    return getattr(m, path[1])

#Dict of Aurora backend instances keyed by thread ID.
#Ensures that two Aurora commands don't interfere by e.g. attempting to write to the same socket.
aurora_backends = dict()
def get_backend():
    thrid = threading.get_ident()
    try:
        return aurora_backends[thrid]
    except KeyError:
        #No backend! Create it.
        backends_list = config.get("scheduler.backends")
        for backend_path in backends_list:
            try:
                backend_class = _importclass(backend_path)
                aurora_backends[thrid] = backend_class()
                break #bail as soon as we get a match
            except (ImportError, AttributeError):
                print("Couldn't find class for backend:", backend_path)
            except backends.BackendInitException as be:
                print("Backend", backend_path, "failed to initialize with error:")
                print(be)
                print("Trying next backend...")

    try:
        return aurora_backends[thrid]
    except KeyError:
        raise backends.BackendInitException("Failed to find a working Aurora backend!")

def pronounceable():
    """Returns 5 characters, consonant vowel consonant vowel consonant for a pronounceable-ish name."""
    consonants = "bcdfghlmnrstvz"
    vowels = "aeiou"
    return random.choice(consonants) + random.choice(vowels) + random.choice(consonants) + random.choice(vowels) + random.choice(consonants)

def gen_jobid(name=''):
    """Generates a new job GUID given a job name."""
    namels = [] if name == "" else [name]
    return "_".join( namels + [ pronounceable(), str(shortuuid.uuid()) ] )

@async.usepool('aurora')
def requestjob(jobrq, vault_api_token):
    """Takes the job request object and converts it into an Aurora definition file.
    Creates a GUID and submits the Aurora definition file to Aurora with the GUID.
    """
    jobid = gen_jobid(jobrq['name'])
    get_backend().requestjob(jobid, jobrq, vault_api_token)
    return jobid

# States that Aurora considers terminal (but may end up rescheduled).
TERMINAL_STATES = ["LOST", "FINISHED", "FAILED", "KILLED"]

# If an Aurora job passes through one of these states, it will always be rescheduled.
RESCHEDULE_STATES = ["RESTARTING", "DRAINING", "PREEMPTING"]

# Additional state we add on top of Aurora's to indicate that a job is Aurora-terminal
# but will be cloned and rescheduled shortly.
RESCHEDULED_STATUS = "RESCHEDULED"


def determine_true_status(jobstatus):
    """Aurora's definition of "terminal state" differs to ours.
    For instance, a job that gets LOST will typically get rescheduled.
    This function takes a job status object and avoids returning a terminal status if it'll be rescheduled.
    It returns a tuple of ("STATUS", { additional_dict }), the latter being extra fields to dump in the output."""
    status = jobstatus.status
    statuslist = [evt.status for evt in jobstatus.taskEvents]
    if status not in TERMINAL_STATES:
        # Job is still in progress.
        return status, {}
    elif any([x in RESCHEDULE_STATES for x in statuslist]):
        # Job is in a terminal state but will be rescheduled.
        # We should hit this rarely as the new task is created (and should therefore go active)
        # at the same time we transition from RESCHEDULE_STATES to TERMINAL_STATES
        return "RESCHEDULED", {}
    elif status == "LOST" and "KILLING" not in statuslist:
        # Job got lost during normal operation and will therefore be rescheduled.
        return "RESCHEDULED", {}
    elif "KILLING" in statuslist:
        # User requested this job was killed. It may actually have ended up in any of TERMINAL_STATES, but it
        # won't be rescheduled, so for simplicity we can hide this to users and pretend it was killed successfully.
        return "KILLED", {}
    elif "FAILED" in statuslist:
        # Might have failed because it went over disk or mem limit. Inspect the message.
        failidx = statuslist.index("FAILED")
        failevt = jobstatus.taskEvents[failidx]
        if failevt.message.startswith("Memory limit exceeded"):
            # Over memory.
            matches = re.findall(r"Memory limit exceeded: Requested (\S+), Used (\S+).", failevt.message)
            assert len(matches) > 0
            return "FAILED", {'reason' : "MEM_EXCEEDED", 'requested': matches[0][0], 'used': matches[0][1]}
        elif failevt.message.startswith("Disk limit exceeded"):
            # Over disk.
            matches = re.findall(r"Disk limit exceeded.  Reserved (\S+) bytes vs used (\S+) bytes.", failevt.message)
            assert len(matches) > 0
            return "FAILED", {'reason' : "DISK_EXCEEDED", 'requested': matches[0][0] + "BYTES", 'used': matches[0][1] + "BYTES"}
        else:
            return status, {}
    else:
        # Job is terminal, wasn't killed, and won't be rescheduled. Report its status truthfully.
        return status, {}


@async.usepool('aurora')
def status(jobid):
    """Return the status of this job ID on Aurora.
    See the Aurora code for a full list of statuses:
            https://github.com/apache/incubator-aurora/blob/61e6c35f91e959ba6247dddc3fe3524795c5f851/api/src/main/thrift/org/apache/aurora/gen/api.thrift#L348
    """
    output = dict()
    output['jobid'] = jobid

    jobresult = get_backend().status(jobid)

    if hasattr(jobresult, 'error') or 'error' in jobresult:
        # {"jobspec":"herc/jclouds/devel/nonexistent_job","error":"No matching jobs found"}
        raise HTTPError(404, "Job ID " + jobid + " not found")
    else:
        # example json is in data/example_aurora_jobstatus.json
        jobresult = jobresult[0]

        # Sort inactive jobs in order of most recent submission time.
        # This catches the issue where a job gets rescheduled but the first run doesn't progress to a terminal state until after the second completes.
        jobruns = jobresult['active'] + sorted(jobresult['inactive'], key=lambda elem: elem.taskEvents[0].timestamp, reverse=True)

        laststatus = jobruns[0]

        output['status'], extradict = determine_true_status(laststatus)
        output['time'] = laststatus.taskEvents[-1].timestamp
        output.update(extradict)

    return output


@async.usepool('aurora')
def kill(jobid):
    """Kills all instances of this task."""

    jobresult = get_backend().kill(jobid)
    return jobresult
