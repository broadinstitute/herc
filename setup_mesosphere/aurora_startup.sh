#!/bin/bash

screen -mdS aurora_sched bash -c 'source aurora_scheduler_startup.sh'
screen -mdS aurora_thermos bash -c 'source aurora_thermos_startup.sh'