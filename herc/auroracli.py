from jinja2 import FileSystemLoader
from jinja2 import Environment
import tempfile
import subprocess
import os
import time

aurora_checked = False
aurora_exists = True

def _aurora_installed():
    """Utility method so we can return stub results for an installation of Herc that's not actually connected to Aurora."""
    # TODO: Swap to the stub Aurora at scheduler init time if no AuroraCLI.
    global aurora_checked
    global aurora_exists

    if not aurora_checked:
        aurora_checked = True
        try:
            with open('/dev/null', 'w') as null:
                subprocess.call(["aurora"], stdout=null, stderr=null)
            aurora_exists = True
        except OSError:
            print "WARNING: aurora not installed, aurora endpoints will return dummy values"
            aurora_exists = False
    return aurora_exists

class AuroraCLI(object):
    """Talk to the Aurora scheduler using the Aurora client."""

    def __init__(self):
        #TODO: throw BackendNotFoundException if no Aurora client, so the scheduler can pick it up and fall back?
        self.loader = FileSystemLoader('jobdefs')
        self.env = Environment(loader=self.loader, trim_blocks=True, lstrip_blocks=True)

    def _build_jinja_dict(self, jobid, jobrq):
        """Takes an ID and job request object and converts it into a Python object for passing to Jinja."""

        # the job request we're going to fill in
        jr = dict()

        # processes to localize down from the "inputs" part of the schema
        downloads = [{'name': "locdown_" + str(idx),
                      'cmd': 'echo localize "' + path['cloud'] + '" "' + path['local'] + '">>localize'}
                     for (idx, path) in enumerate(jobrq['inputs'])]

        # processes to localize back up to the cloud from the "outputs" part of the schema
        uploads = [{'name': "locup_" + str(idx),
                    'cmd': 'echo localize "' + path['local'] + '" "' + path['cloud'] + '">>localize'}
                   for (idx, path) in enumerate(jobrq['outputs'])]

        # list of processes: download, run the commandline, upload
        jr['processes'] = downloads + [{'name': jobid + '_ps', 'cmd': jobrq['commandline']}] + uploads

        # Currently all we need is one task, made of the list of download + run + upload processes.
        # We don't (yet?) need to do anything clever with Tasks.concat() or combine(), and the template doesn't support it.
        # The last task in this list will be used as the task to run on the job, so if we ever do use Tasks.concat() or
        # combine(), that should be the final task in this list.
        jr['tasks'] = [{'name': jobid + '_task',
                        'type': 'SequentialTask',
                        'processes': [p['name'] for p in jr['processes']],
                        'cpus': jobrq['resources']['cpus'],
                        'mem': jobrq['resources']['mem'],
                        'memunit': jobrq['resources']['memunit'],
                        'disk': jobrq['resources']['disk'],
                        'diskunit': jobrq['resources']['diskunit']
                       }]

        # as above: we assume the tasks list has been constructed such that the last task
        # in the list is the one we want to execute for this job.
        jr['jobs'] = [{'name': jobid,
                       'task': jr['tasks'][-1]['name'],
                       'env': 'devel',  # configurable?
                       'cluster': 'herc',  # also configurable?
                       'hostlimit': 99999999,
                       'container': jobrq['docker']
                       # instance configuration goes here, if we ever use it
                      }]

        return jr

    def requestjob(self, jobid, jobrq):
        jr = self._build_jinja_dict(jobid, jobrq)

        template = self.env.get_template('jobtemplate.aurora')
        tmpfile = tempfile.NamedTemporaryFile(suffix=".aurora")

        # might error.
        tmpfile.write(template.render(jr).encode('utf-8'))
        tmpfile.flush()
        os.fsync(tmpfile.fileno())

        # what does aurora return here?
        # we could parse the output...
        then = time.time()
        subprocess.call(['aurora', 'job', 'create', 'herc/jclouds/devel/' + jobid, tmpfile.name])
        auroratime = time.time() - then

        # don't do this until after the job is submitted
        tmpfile.close()

    def status(self, jobid):
        then = time.time()
        resjson = subprocess.check_output(['aurora', 'job', 'status', 'herc/jclouds/devel/' + jobid, "--write-json"])
        auroratime = time.time() - then
        return resjson
