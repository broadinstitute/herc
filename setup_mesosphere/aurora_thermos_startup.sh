#!/bin/bash

exec ~/aurora-src/dist/thermos_observer.pex \
  --root=/var/run/thermos \
  --port=1338 \
  --log_to_disk=NONE \
  --log_to_stderr=google:INFO