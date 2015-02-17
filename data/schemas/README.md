# herc submit JSON schema

This file describes the JSON schema required for submitting jobs to herc.

## Example

Below is an example JSON `/submit` payload.

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

#### `inputs`
A list of input files to localize. (If you don't have any, just pass an empty list.) You can have as many of these as you like. The values for `cloud` must be either `gcs://` or `boss://` file paths. The values for `local` must be local file paths.

####`commandline`
The command line to run inside the docker.

####`docker`
The docker image to pull and spin up. **This docker image must have Python 2.7 installed, or the Aurora executor won't be able to run.**

####`resources`
The list of Mesos resources to request for this task. `cpus`, `mem`, and `disk` are mandatory; `memunit` and `diskunit` are optional and will be set to `"MB"` if you don't specify them.

####`outputs`
A list of files to upload back to the cloud after the work is done. The value for `cloud` must be a `gcs://` file path (`boss://` isn't supported for upload).

## Testing

You can pull the latest version of the schema over the REST API with `GET /schema`, or then look at [jobsubmit.json](jobsubmit.json) above.

You can then check your generated JSON against the schema using the handy online validator [here](http://json-schema-validator.herokuapp.com/).