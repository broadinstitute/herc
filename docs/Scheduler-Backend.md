This document explains the level of indirection between herc's *scheduler* module and the multiple *backends* it supports.

The **scheduler** is `aurorasched.py`. Herc's various endpoints may choose to call functions on this module when it wants to talk to Aurora. A **backend** wraps talking to the Aurora scheduler somehow. The scheduler chooses which backend to use, passes on requests, and interprets the responses in a standard way.

More?

# The Scheduler

The scheduler's responsibilities are twofold:

1. Make well-formed requests to a backend (see [the backend interface](#the-backend-interface) below); and
2. Interpret the results the backend returns.

The scheduler can then do any post-processing on the backend's responses. In practice this means remapping Aurora's task statuses into clearer Herc ones.

The scheduler chooses which backend to instantiate based off the [configuration file](Configuration.md).

# Backends

A backend's responsibility is to talk to the Aurora scheduler *somehow*.

Each backend uses a different method to do this:

* `AuroraCLI`: uses the Aurora client executable;
* `AuroraThrift` (yet to be written, but coming soon!): uses Aurora's Thrift interface;
* `AuroraMock`: returns the same pre-packaged response for every request (for testing purposes). 

## The backend interface

Backend classes must implement the following methods:

##### `def __init__(self):`

Will be called with no arguments to set up the backend. This method may `raise herc.aurorabackend.BackendInitException()` to notify the calling scheduler that this backend cannot be initialized (perhaps because its dependencies don't exist).

##### `def requestjob(self, jobid, jobrq):`

Submit a job with the given id and other (`jobrq`) parameters to Aurora.

**Inputs**

* `jobid` will be a string that will be used to uniquely identify this job in future. The backend *must* use this as the name of the top-level [Job](http://aurora.incubator.apache.org/documentation/latest/configuration-reference/#job-schema) in the submit request to Aurora; this ensures that other backends can find the resulting job when asked to via `status()`.
* `jobrq` will be a Python object generated from a correctly validated [`/submit`](API.md#post-submit) request using the [JSON schema](../data/schemas/jobsubmit.json). Any optional values defined by the schema will be filled in with their default values if they weren't present in the original request.

**Output**

`None`

##### `def status(self, jobid):`

Request an update on the status of the job with `jobid`.

**Inputs**

* `jobid` The name of an Aurora job, previously passed to a `requestjob()` call on some backend. This backend is *not* guaranteed to be the same instance or even a backend of the same class\! This should essentially translate to an Aurora lookup of the job `cluster/role/env/<jobid>`.

**Output**

* A Python object representing the job's status and history. A JSON-serialized version of what this looks like is [here](../data/stub_aurora_jobstatus.json); a more complex example is [here](../data/example_aurora_jobstatus.json). 

##### `def kill(self, jobid):`

Kills all running instances of the job with id `jobid`.

**Inputs**

* `jobid` The name of an Aurora job, previously passed to a `requestjob()` call on some backend.

**Output**

* If the job exists or doesn't, a dict with the key `success` and value either `Job not found.` or `Job killed.`, depending on whether the job was found.
* If the call fails for some other reason, a dict with the key `error` and a string value containing more details.
