# Read live data from CMS50D+ finger oximeter
### Display in real time and issue vibrational alarm on external android smartphone
### Bedside-friendly

This Python app reads live data from a (easily available and reasonably priced) CMS50D+ v4.6 finger oximeter. Displays a real time plot of the oxygen saturation (SpO2) and pulse rate (PR) as well as the present values. Activates an external smartphone vibration via Bluetooth if SpO2 descends below an adjustable minimum value. Disconnections/errors are handled gracefully.

This was developed to help with idiopathic central sleep apnea. Obviously, it is provided “as is”, without any implication that it may be useful to anyone’s specific case.

Optionally stores in disk at every heartbeat the SpO2 and hearth rate as displayed by the oximeter, the time from the last heartbeat (RR time), max, min and average for the last heartbeat of the two pulse waveforms outputted (probably the red and infrared channels). An example matlab script is provided to read and analyze this information.

The present version was tested under Lubuntu 12.04 on Eee PC 4G and under Ubuntu 18.04 on a modern laptop. The smartphone was under Android Go.

Optionally the oximeter can be modified to be powered from the data cable to avoid using batteries.

See **Instructions.pdf** for details.


# ----------------------------------
This code includes contributions/info from:\
https://www.snip2code.com/Snippet/1802729/Read-live-data-from-a-CMS50D--pulse-oxim \
https://github.com/airikka/spo2cms50dplus \
https://github.com/atbrask/CMS50Dplus

For downloading the data stored in the oximeter see\
https://github.com/airikka/spo2cms50dplus
