# herc.conf file format

As per DSDE standard this is a [HOCON](https://github.com/typesafehub/config/blob/master/HOCON.md) file.

### Sample contents

`scheduler.backends=[herc.auroracli.AuroraCLI, herc.aurorastub.AuroraStub]`

A list of Python import paths to Herc scheduler backends. Herc will attempt to make a backend of each type in turn, stopping at (and using) the first backend that doesn't raise `aurorabackend.BackendInitException`.
