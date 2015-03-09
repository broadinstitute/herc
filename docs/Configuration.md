# herc.conf file format

As per DSDE standard this is a [HOCON](https://github.com/typesafehub/config/blob/master/HOCON.md) file.

### Sample contents

`scheduler.backends=[herc.backends.AuroraCLI, herc.backends.AuroraMock]`

A list of Python import paths to Herc scheduler backends. Herc will attempt to make a backend of each type in turn, stopping at (and using) the first backend that doesn't raise `herc.backends.BackendInitException`.

`auroracli.localizecmd="python /job/task/transfer.py"`

Script or executable available in the execution environment (probably Docker) for the task. This script must take two arguments, and copy the contents of the first argument to the second.
