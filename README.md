# Read live data from CMS50D+ finger oximeter
## Store values and post alarm accessible over LAN

This program reads live data from a (easily available and reasonably priced) CMS50D+ oximeter and stores in disk at every heartbeat the SpO2% and hearth rate as displayed by the oximeter, the time from the last heartbeat, max, min and average for the last heartbeat of the two pulse waveforms outputted (probably the red and infrared channels).

Upon a predefined (-a option) SpO2 level a json file (comando.json) is stored in a designated folder. This can be read over web by an external web app to raise an alarm. E.g.: in a browser http://IPofRunningPC:8000/comando.json \
Can be easily adapted to include other data/actions.

Sensor disconnections/errors are handled gracefully.

Practical tips for long time acquisition:
- The battery alarm goes on at a very early stage, after a couple of hours, but it actually lasts up to 8h. Unfortunately this renders the alarm useless after a couple of hours as it will start to report a low battery. This is one of my motivations to write this program. The other is that I wanted a more progressive/smart alarm.
- Turning on the Record option in the oximeter auto shuts-off the display, saving battery.

# ----------------------------------
Setup:\
(ubuntu; other OS please google)\
sudo usermod -a -G dialout $USER # then log out and in again. This gives user access to /dev/ttyUSBx via dialout group\
sudo apt-get install python-dateutil python-serial  # python dependencies

Usage:\
./BreatheIn.py\
Use -h option to display help\
Reasonable defaults are assumed if called without arguments.

Launcher:\
./BreatheIn.sh\
This launches Python's SimpleHTTPServer to serve the alarm file on /tmp\
Passes optional args for BreatheIn.py\
Tested in Ubuntu 18.04, Lubuntu 12.04. Should be subtly altered for for other OS.

Viewer:\
BreatheIn.m\
Matlab R2012a script. May work in Octave, but untested.\
Sample data is provided.

# ----------------------------------
This code includes contributions/info from:\
https://www.snip2code.com/Snippet/1802729/Read-live-data-from-a-CMS50D--pulse-oxim \
https://github.com/airikka/spo2cms50dplus \
https://github.com/atbrask/CMS50Dplus

For download of the data stored in the oximeter see\
