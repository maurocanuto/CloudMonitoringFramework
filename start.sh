#!/bin/bash
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root"
   exit 1
fi

nohup ./init_parallel.py start  >/dev/null 2>&1 &  # doesn't create nohup.out
