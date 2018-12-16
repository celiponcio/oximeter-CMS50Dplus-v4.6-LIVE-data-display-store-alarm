#!/usr/bin/env bash
# do this before
# sudo usermod -a -G dialout $USER 
# sudo apt-get install python-dateutil python-serial # OR could not open port /dev/ttyUSB0: [Errno 13] Permission denied: '/dev/ttyUSB0'
# close session and reopen
(cd /tmp; python -m SimpleHTTPServer 8000) &
./BreatheIn.py -c /tmp -o $1 $2 $3 $4
pkill python
