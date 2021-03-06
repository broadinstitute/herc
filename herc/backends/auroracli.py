from jinja2 import FileSystemLoader
from jinja2 import Environment
import tempfile
import subprocess
import os
import time
import logging
import arrow
import munch
from .. import config
from .aurorabackend import BackendInitException

aurora_checked = False
aurora_exists = True

log = logging.getLogger('herc.backends.auroracli')

def run(cmd, cwd=None):
    start = arrow.utcnow()
    proc = subprocess.Popen(
        cmd,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        cwd=cwd
    )
    stdout, stderr = proc.communicate()
    elapsed = arrow.utcnow() - start
    log.info('run(): [time={0}, rc={1}] {2}'.format(elapsed, proc.returncode, ' '.join(cmd)))
    return (proc.returncode, stdout.strip(' \n'), stderr.strip(' \n'))

def _aurora_installed():
    """Utility method to determine if the Aurora client actually exists."""
    global aurora_checked
    global aurora_exists

    if not aurora_checked:
        aurora_checked = True
        try:
            run(['aurora'])
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
        self.kill_cmd = config.get("auroracli.killcmd").split()
        self.cluster = config.get("aurora.cluster.name")
        self.role = config.get("aurora.cluster.role")
        self.env = config.get("aurora.cluster.env")

    @staticmethod
    def _build_jinja_dict(jobid, jobrq, localize_cmd, vault_api_token):
        """Takes an ID and job request object and converts it into a Python object for passing to Jinja."""

        flags = ''
        if vault_api_token:
            flags = "--vault-api-token='{0}'".format(vault_api_token)

        # the job request we're going to fill in
        jr = dict()

        symlink_dir = '/mnt/mesos/sandbox/sandbox/__jobio'
        setup = [
            {'name': 'mkdir', 'cmd': 'mkdir -p {0}/input {0}/output'.format(symlink_dir)},
            {'name': 'symlink_in', 'cmd': 'ln -s {}/input /job/input'.format(symlink_dir)},
            {'name': 'symlink_out', 'cmd': 'ln -s {}/output /job/output'.format(symlink_dir)}
        ]

        # processes to localize down from the "inputs" part of the schema
        downloads = [{'name': "locdown_" + str(idx),
                      'cmd': '{0} "{1}" "{2}" {3}'.format(localize_cmd, path['cloud'], path['local'], flags).strip()}
                     for (idx, path) in enumerate(jobrq['inputs'])]

        # processes to localize back up to the cloud from the "outputs" part of the schema
        uploads = [{'name': "locup_" + str(idx),
                    'cmd': '{0} "{1}" "{2}" {3}'.format(localize_cmd, path['local'], path['cloud'], flags).strip()}
                   for (idx, path) in enumerate(jobrq['outputs'])]

        # list of processes: download inputs, run the commandline, upload outputs
        jr['processes'] = setup + downloads + [{'name': jobid + '_ps', 'cmd': jobrq['commandline']}] + uploads

        #finalizing processes to localize stdout and stderr up to gcs
        #these are guaranteed to run even if the task fails because one of the other processes fail.
        jr['finalizers'] = []
        if jobrq['stdout'] != "":
            jr['finalizers'].append({
                'name' : "__locup_stdout",
                'cmd' : '{0} ".logs/{1}_ps/0/stdout" "{2}" {3}'.format(localize_cmd, jobid, jobrq['stdout'], flags).strip()
            })
        if jobrq['stderr'] != "":
            jr['finalizers'].append({
                'name' : "__locup_stderr",
                'cmd' : '{0} ".logs/{1}_ps/0/stderr" "{2}" {3}'.format(localize_cmd, jobid, jobrq['stderr'], flags).strip()
            })

        # Currently all we need is one task, made of the list of download + run + upload processes.
        # We don't (yet?) need to do anything clever with Tasks.concat() or combine(), and the template doesn't support it.
        # The last task in this list will be used as the task to run on the job, so if we ever do use Tasks.concat() or
        # combine(), that should be the final task in this list.
        jr['tasks'] = [{'name': jobid + '_task',
                        'processes': [p['name'] for p in jr['processes']] + [p['name'] for p in jr['finalizers']],
                        'ordering': [p['name'] for p in jr['processes']],
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

    def requestjob(self, jobid, jobrq, vault_api_token):
        jr = self._build_jinja_dict(jobid, jobrq, self.localize_cmd, vault_api_token)

        template = self.template_env.get_template('jobtemplate.aurora')
        tmpfile = tempfile.NamedTemporaryFile(suffix=".aurora")

        # might error.
        tmpfile.write(template.render(jr).encode('utf-8'))
        tmpfile.flush()
        os.fsync(tmpfile.fileno())

        # what does aurora return here?
        # we could parse the output...
        # Boils down to: aurora job create cluster/role/env/jobid jobfile.tmp
        (rc, stdout, stderr) = run(self.submit_cmd + ['/'.join([self.cluster, self.role, self.env, jobid]), tmpfile.name])

        # don't do this until after the job is submitted
        tmpfile.close()

    def status(self, jobid):
        # Boils down to: aurora job status cluster/role/env/jobid --write-json
        (rc, stdout, stderr) = run(self.status_cmd + ['/'.join([self.cluster, self.role, self.env, jobid]), "--write-json"])
        jobresult = json.loads(stdout)
        # scheduler expects a munchified object 
        munchifiedresult = munch.munchify(jobresult)
        return munchifiedresult

    def kill(self, jobid):
        # Boils down to: aurora job killall cluster/role/env/jobid
        (rc, stdout, stderr) = run(self.kill_cmd + ['/'.join([self.cluster, self.role, self.env, jobid])])
        outlines = stdout.split('\n')
        errlines = stderr.split('\n')

        if outlines[-1].strip() == "Job killall succeeded":
            if errlines[-1].strip().startswith("No tasks to kill found"):
                return { "success" : "Job not found." }
            else:
                return { "success" : "Job killed." }
        else:
            return { "error" : stderr }
