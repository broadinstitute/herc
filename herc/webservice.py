from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.web import RequestHandler, Application
from tornado import gen
from tornado import httpserver
from collections import OrderedDict
import inspect
import argparse
import os.path
import subprocess
import json
import time
from . import async
from . import jsonvalidate
from . import aurorasched as scheduler
from . import config


class base(RequestHandler):

    def initialize(self):
        self.set_header('Content-Type', 'application/json')
        self.set_header('Access-Control-Allow-Origin',	   '*')
        self.set_header('Access-Control-Allow-Credentials', 'true')

    def write_error(self, status_code, **kwargs):
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            super(base, self).write_error(status_code, **kwargs)
        else:
            log_msg = None
            try:
                log_msg = kwargs['exc_info'][1].log_message
            except (KeyError, AttributeError):
                pass
            finally:
                log_msg = self._reason if log_msg is None else log_msg

            self.set_header('Content-Type', 'application/json')
            self.finish(json.dumps({
                "code": status_code,
                "message": log_msg
            }))


class index(base):

    def get(self):
        """GET /
        Returns the list of endpoints that this webservice provides."""
        global endpoint_mapping
        self.write(json.dumps(self.prettify(endpoint_mapping), indent=1))
        self.finish()

    def prettify(self, endpoint_mapping):
        """Constructs a dict of endpoints and their descriptions, pulled from the docstrings of the endpoint classes themselves."""
        http_methods = [http_method.lower() for http_method in RequestHandler.SUPPORTED_METHODS]
        http_request_handlers = list(endpoint_mapping.values())

        # Get doc strings for all functions in RequestHandlers.  Only non-empty doc strings for http methods are returned
        doc_strings = [inspect.getdoc(function)
            for handler in http_request_handlers
            for function in list(dict(inspect.getmembers(handler)).values())
            if inspect.isfunction(function)
               and function.__name__ in http_methods
               and inspect.getdoc(function) is not None
        ]

        docs_dictionary = OrderedDict([
            (doc_string.split('\n', 1)[0], doc_string.split('\n', 1)[1]) for doc_string in sorted(doc_strings)
        ])

        return docs_dictionary


class schema(base):

    def get(self):
        """GET /schema
        Returns the JSON schema used to validate job submission requests."""
        with open("data/schemas/jobsubmit.json", 'r', encoding="utf-8") as jschema:
            self.write(jschema.read())
            self.finish()


class submit(base):

    @gen.coroutine
    def post(self):
        """POST /submit
        Submits a job request. Body must be JSON that validates against the JSON schema available at GET /schema. Returns a JSON object, { "jobid" : "<new_job_id>" }."""

        # Validate the request against the schema, filling in defaults. This will raise an HTTPError if it fails validation.
        jobrq = yield jsonvalidate.validate(self.request.body.decode('utf-8'), "data/schemas/jobsubmit.json")
        jobid = yield scheduler.requestjob(jobrq)

        self.write(json.dumps({'jobid': jobid}))
        self.finish()


class status(base):

    @gen.coroutine
    def get(self, jobid):
        """GET /status/<jobid>
        Query Aurora and return the status of this job. 404 if not found, otherwise will return JSON with the job's current status and the time it entered that status."""
        status = yield scheduler.status(jobid)
        self.write(json.dumps(status, indent=1))
        self.finish()


class sleep(base):

    @gen.coroutine
    def get(self, n=0):
        """GET /sleep/<n>
        Sleep for n seconds and then return."""
        ret = yield self.sleep(int(n))
        self.write(ret)

    @async.usepool('long')
    def sleep(self, secs):
        then = time.time()
        time.sleep(secs)
        return "Slept for " + str(time.time() - then) + " seconds"

endpoint_mapping = {
    r'/': index,
    r'/schema/?': schema,
    r'/submit/?': submit,
    r'/status/(.*)/?': status,
    r'/sleep/(.*)/?': sleep
}


def main():
    parser = argparse.ArgumentParser(description='Herc', epilog='The Broad Institute')
    parser.add_argument(
        '-D', '--debug', required=False, default=False, action='store_true', help='Run server in foreground'
    )
    parser.add_argument(
        '-p', '--port', default=4372, help='Server TCP port'
    )
    cli = parser.parse_args()

    if cli.debug:
        print('Started Herc in DEBUG mode (port {0})'.format(cli.port))
        from tornado.log import enable_pretty_logging
        enable_pretty_logging()

    #Force a config load so we exit early if we fail to load one.
    config.load_config(['/etc/herc.conf', 'herc.conf'])

    # Generate a self-signed certificate and key if we don't already have one.
    if not os.path.isfile("herc.crt") or not os.path.isfile("herc.key"):
        subprocess.call('openssl req -x509 -newkey rsa:2048 -keyout herc.key -out herc.crt -days 36500 -nodes -subj'.split() + ["/C=US/ST=MA/L=Cambridge/O=Broad Institute/OU=Prometheus"])

    app = Application(list(endpoint_mapping.items()), compress_response=True, debug=cli.debug)
    ili = IOLoop.instance()

    http_server = httpserver.HTTPServer(app,
                                        ssl_options={
                                            "certfile": "herc.crt",
                                            "keyfile": "herc.key"},
                                        io_loop=ili)
    http_server.listen(cli.port)

    # Trigger a callback that does nothing every half-second so KeyboardInterrupts can actually get through
    PeriodicCallback(lambda: None, 500, ili).start()
    ili.start()
