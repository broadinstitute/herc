# Herc API

This file gives more details on the Herc API.

Examples are given with [cURL](http://curl.haxx.se/docs/) and [HTTPie](https://github.com/jakubroztocil/httpie), assuming the server is running on `localhost:4372` with self-signed certificates (i.e. do not try to verify SSL certificates).  Some of the HTTP request output may be truncated due to length.

## `GET /`

Returns a list of endpoints and brief descriptions. This is always accurate; the document you're reading now may not be!

### Example

HTTPie:
```bash
$ http --verify=no https://localhost:4372/
```

cURL:
```bash
$ curl -i --insecure https://localhost:4372/
```

Response:
```http
HTTP/1.1 200 OK
Access-Control-Allow-Credentials: true
Access-Control-Allow-Origin: *
Content-Encoding: gzip
Content-Length: 331
Content-Type: application/json
Date: Thu, 26 Feb 2015 15:33:37 GMT
Etag: "1a5eae502514465d016ec0e4f63ced4e52ef348c"
Server: TornadoServer/4.1
Vary: Accept-Encoding

{
    "GET /": "Returns the list of endpoints that this webservice provides.",
    "GET /schema": "Returns the JSON schema used to validate job submission requests.",
    "GET /sleep/<n>": "Sleep for n seconds and then return.",
    "GET /status/<jobid>": "Query Aurora and return the status of this job. 404 if not found, otherwise will return JSON with the job's current status and the time it entered that status.",
    "POST /submit": "Submits a job request. Body must be JSON that validates against the JSON schema available at GET /schema. Returns a string, the job ID."
}
```

## `GET /schema`

Returns the [JSON schema](http://json-schema.org/) used to validate job submissions sent to `GET /submit`.

### Example

HTTPie:
```bash
$ http --verify=no https://localhost:4372/schema 
```

cURL:
```bash
$ curl -i --insecure https://localhost:4372/schema
```

Response:
```http
HTTP/1.1 200 OK
Access-Control-Allow-Credentials: true
Access-Control-Allow-Origin: *
Content-Encoding: gzip
Content-Length: 452
Content-Type: application/json
Date: Thu, 26 Feb 2015 15:42:07 GMT
Etag: "ac88412bb1f830bdcb1333b017a574706a220ac0"
Server: TornadoServer/4.1
Vary: Accept-Encoding

{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "definitions": {
        "bytesunit": {
            "default": "MB",
            "pattern": "^BYTES|^KB|^MB|^GB|^TB",
            "type": "string"
        },
    ... truncated ...
}
```

## `POST /submit`

Expects a JSON body that validates against the schema returned by `GET /schema`. Returns a JSON object, `{ "jobid" : "<new_job_id>" }`.

The schema is defined [here](../data/schemas/jobsubmit.json) (and `GET /schema` simply returns the contents of this file). You can then check your generated JSON against the schema using the handy online validator [here](http://json-schema-validator.herokuapp.com/).

Below is an example payload:

```JSON
{
    "inputs" : [
        {
            "cloud" : "gcs://foo",
            "local" : "/foo"
        },
        {
            "cloud" : "boss://bar",
            "local" : "/bar"
        }
    ],
    "commandline" : "echo Hello herc! > /baz",
    "docker" : "python:2.7",
    "resources" : {
        "cpus" : 1,
        "mem" : 16,
        "memunit" : "MB",
        "disk" : 1,
        "diskunit" : "GB"
    },
    "outputs" : [
        {
            "cloud" : "gcs://baz",
            "local" : "/baz"
        }
    ]
}
```

##### `inputs`
A list of input files to localize. (If you don't have any, just pass an empty list.) You can have as many of these as you like. The values for `cloud` must be either `gcs://` or `boss://` file paths. The values for `local` must be local file paths.

#####`commandline`
The command line to run inside the docker.

#####`docker`
The docker image to pull and spin up. **This docker image must have Python 2.7 installed, or the Aurora executor won't be able to run.**

#####`resources`
The list of Mesos resources to request for this task. `cpus`, `mem`, and `disk` are mandatory; `memunit` and `diskunit` are optional and will be set to `"MB"` if you don't specify them.

#####`outputs`
A list of files to upload back to the cloud after the work is done. The value for `cloud` must be a `gcs://` file path (`boss://` isn't supported for upload).

### Example

HTTPie:
```bash
$ http --verify=no POST https://localhost:4372/submit @testjob.json
```

cURL:
```bash
$ curl -H "Content-Type: application/json" -X POST -d @testjob.json --insecure https://localhost:4372/submit
```

Response:
```http
HTTP/1.1 200 OK
Access-Control-Allow-Credentials: true
Access-Control-Allow-Origin: *
Content-Encoding: gzip
Content-Length: 60
Content-Type: application/json
Date: Thu, 26 Feb 2015 15:54:03 GMT
Server: TornadoServer/4.1
Vary: Accept-Encoding

{
    "jobid": "job_d46ce9fd_325c_4f32_a287_c36b790fa9ff"
}
```

## `GET /status/<jobid>`

Query Aurora and return the status of the job id. Will return HTTP 404 if not found, otherwise will return JSON with the job's current status and the time it entered that status.

Because Aurora's definition of "terminal states" doesn't preclude a job being rescheduled, Herc may return a different status that more accurately represents what's happening with the job. Here's what you need to know:

* `FINISHED`, `FAILED`, `KILLED`, `MEM_EXCEEDED` and `DISK_EXCEEDED` are the only terminal states. Any other state is non-terminal. You will never see the Aurora state `LOST`; Herc turns it into either `RESCHEDULED` or `KILLED` (see below).
* `RESCHEDULED` is a non-terminal state added by Herc that indicates Aurora is in the process of rescheduling a job. This can happen when a job gets lost, pre-empted by a higher priority job, or the node it was running on is put into maintenance.
* `MEM_EXCEEDED` and `DISK_EXCEEDED` are terminal states that indicate the job failed because it exceeded the amount of memory or disk it requested in its Resources struct. In this case the JSON payload will contain two additional fields, `requested` and `used`; the values of both are strings, e.g. `128MB` or `3145728BYTES`.
* `KILLED` exclusively means "killed on request by a user or admin". It will be returned even if the job completes, fails, or gets lost before or during the execution of the kill request.

### Example

HTTPie:
```bash
$ http --verify=no https://localhost:4372/status/job_795aca97_8678_4af7_ade1_e4fadd7bff78
```

cURL:
```bash
$ curl --insecure https://localhost:4372/status/job_795aca97_8678_4af7_ade1_e4fadd7bff78
```

Response:
```http
HTTP/1.1 200 OK
Access-Control-Allow-Credentials: true
Access-Control-Allow-Origin: *
Content-Encoding: gzip
Content-Length: 115
Content-Type: application/json
Date: Thu, 26 Feb 2015 16:11:32 GMT
Etag: "6965df488267a089cf5b2e245bb38d33c4628551"
Server: TornadoServer/4.1
Vary: Accept-Encoding

{
    "jobid": "job_795aca97_8678_4af7_ade1_e4fadd7bff78",
    "status": "PENDING",
    "time": 1424966044800
}
```

## `GET /sleep/<n>`

Test endpoint that keeps the connection open for n seconds and then returns how long it was open for.
