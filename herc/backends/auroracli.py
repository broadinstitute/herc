from jinja2 import FileSystemLoader
from jinja2 import Environment
import tempfile
import subprocess
import os
import time
from .. import config
from .aurorabackend import BackendInitException

aurora_checked = False
aurora_exists = True

def _aurora_installed():
    """Utility method to determine if the Aurora client actually exists."""
    global aurora_checked
    global aurora_exists

    if not aurora_checked:
        aurora_checked = True
        try:
            with open('/dev/null', 'w') as null:
                subprocess.call(["aurora"], stdout=null, stderr=null)
            aurora_exists = True
        except OSError:
            aurora_exists = False
    return aurora_exists

class AuroraCLI(object):
    """Talk to the Aurora scheduler using the Aurora client."""

    def __init__(self):
        if not _aurora_installed():
            raise BackendInitException("Aurora client not found, cannot initialize AuroraCLI backend")

        self.loader = FileSystemLoader('jobdefs')
        self.template_env = Environment(loader=self.loader, trim_blocks=True, lstrip_blocks=True)
        self.localize_cmd = config.get("auroracli.localizecmd")
        self.submit_cmd = config.get("auroracli.submitcmd").split()
        self.status_cmd = config.get("auroracli.statuscmd").split()
        self.cluster = config.get("aurora.cluster.name")
        self.role = config.get("aurora.cluster.role")
        self.env = config.get("aurora.cluster.env")

    @staticmethod
    def _build_jinja_dict(jobid, jobrq, localize_cmd):
        """Takes an ID and job request object and converts it into a Python object for passing to Jinja."""

        # the job request we're going to fill in
        jr = dict()

        # processes to localize down from the "inputs" part of the schema
        downloads = [{'name': "locdown_" + str(idx),
                      'cmd': localize_cmd + ' "' + path['cloud'] + '" "' + path['local'] + '"'}
                     for (idx, path) in enumerate(jobrq['inputs'])]

        # processes to localize back up to the cloud from the "outputs" part of the schema
        uploads = [{'name': "locup_" + str(idx),
                    'cmd': localize_cmd + ' "' + path['local'] + '" "' + path['cloud'] + '"'}
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
        jr = self._build_jinja_dict(jobid, jobrq, self.localize_cmd)

        template = self.template_env.get_template('jobtemplate.aurora')
        tmpfile = tempfile.NamedTemporaryFile(suffix=".aurora")

        # might error.
        tmpfile.write(template.render(jr).encode('utf-8'))
        tmpfile.flush()
        os.fsync(tmpfile.fileno())

        # what does aurora return here?
        # we could parse the output...
        then = time.time()
        #boils down to: aurora job create cluster/role/env/jobid jobfile.tmp
        subprocess.call(self.submit_cmd + ['/'.join([self.cluster, self.role, self.env, jobid]), tmpfile.name])
        auroratime = time.time() - then

        # don't do this until after the job is submitted
        tmpfile.close()

    def status(self, jobid):
        then = time.time()
        #boils down to: aurora job status cluster/role/env/jobid --write-json
        resjson = subprocess.check_output(self.status_cmd + ['/'.join([self.cluster, self.role, self.env, jobid]), "--write-json"])
        auroratime = time.time() - then
        return resjson
