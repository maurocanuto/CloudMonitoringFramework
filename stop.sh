#!/bin/bash
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root"
   exit 1
fi

./init_parallel.py stop
