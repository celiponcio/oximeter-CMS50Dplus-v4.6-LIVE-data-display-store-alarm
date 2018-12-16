###################################################################
Read live data from CMS50D+ finger oximeter\
Store values and post alarm accessible over LAN\
###################################################################

This program reads live data from a CMS50D+ oximeter and stores in disk at every heartbeat the SpO2% and hearth rate as displayed by the oximeter, the time from the last heart beat, max, min and average of the pulse waveform for the last heartbeat and the same for a related signal that is output but I'm not sure what it means.

Upon a predefined SpO2 level a json file (comando.json) is stored in a designated folder. This can be readout over web by an external web app to raise an alarm. E.g.: in a browser http://IPofRunningPC:8000/comando.json\
Can be easily adapted to include other data/actions.

Setup:\
(linux; other OS please google)\
sudo usermod -a -G dialout $USER # then logout and in again. This gives user access to /def/ttyUSBx via dialout group\
sudo apt-get install python-dateutil python-serial  # python dependencies

Usage:\
       BreatheIn.py [-h] [-a ALARM_MIN_SPO2] [-d DEVICE] [-c COMMANDFILE_PATH]\
                    [-o]\
optional arguments:\
  -h, --help            show this help message and exit\
  -a ALARM_MIN_SPO2, --alarm_min_SpO2 ALARM_MIN_SPO2\
                        Alarm SpO2 minimal level\
  -d DEVICE, --device DEVICE\
                        Path to device. Default: /dev/ttyUSB0\
  -c COMMANDFILE_PATH, --commandfile_path COMMANDFILE_PATH\
                        Command file path. Default=current folder\
  -o, --output          Store data on current folder

Launcher:\
BreatheIn.sh\
This launches Python's SimpleHTTPServer to serve the alarm file on /tmp\
Passes optional args for BreatheIn.py\
Tested in Ubuntu 18.04, Lubuntu 12.04. Should be subtly altered for for other OS.

Viewer:\
BreatheIn.m\
Matlab R2012a. May work in Octave, but untested.\
Sample data is provided.

# ----------------------------------\
This code includes contributions/info from:\
https://www.snip2code.com/Snippet/1802729/Read-live-data-from-a-CMS50D--pulse-oxim\
https://github.com/airikka/spo2cms50dplus\
https://github.com/atbrask/CMS50Dplus

For download of the data stored in the oximeter see\
https://github.com/airikka/spo2cms50dplus
