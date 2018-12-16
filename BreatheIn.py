#!/usr/bin/env python2

# derived from:
# https://www.snip2code.com/Snippet/1802729/Read-live-data-from-a-CMS50D--pulse-oxim
# 
# Copyright (c) 2018  celiponcio <celiponcio1@sapo.pt>
# License: GPLv2


import struct, serial, argparse, datetime, time
import dateutil.parser
import signal, sys
import csv

#####################
##### Variables #####
#####################

alarm_pause=10

parser = argparse.ArgumentParser(description="Download live data from a CMS50D+ oximeter. Store at every heart beat with time.")
parser.add_argument('-a','--alarm_min_SpO2', type=int, help='SpO2 minimal level',default=94, required=False)
parser.add_argument('-d','--device', type=str, help='path to device', default='/dev/ttyUSB0', required=False)
parser.add_argument('-c','--commandfile_path', type=str, help='command file path',default='.', required=False)
#parser.add_argument('-o','--outfile', type=str, help='output file path',default=False, required=False)
parser.add_argument('-o','--output',action='store_true',default=False)
args = parser.parse_args()

alarm_min_SpO2=args.alarm_min_SpO2
device = args.device
output = args.output
commandfile_path=args.commandfile_path
print alarm_min_SpO2, device, commandfile_path, output
ser = serial.Serial()
outfile=datetime.datetime.now().strftime("%Y%m%d%H%M%S")+"_BreatheIn.csv"

###################
##### Helpers #####
###################

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    do_alarm(0, 0, alarm_pause)  # kill alarm
    ser.close()
    sys.exit(0)

#####################
##### Functions #####
#####################

def configure_serial(ser):
    ser.baudrate = 115200  # 115200
    ser.bytesize = serial.EIGHTBITS  # 8
    ser.parity = serial.PARITY_NONE  # NONE
    ser.stopbits = serial.STOPBITS_ONE  # 1
    ser.xonxoff = 1  # XON/XOFF flow control
    ser.timeout = 3
    ser.port = device

# ------------------------------------------------
def main_loop(ser):
    sys.stdout.write("Connecting to device...\n")
    sys.stdout.flush()

    try:
        ser.open()
    except Exception as ex:
        print(ex)
        ser.close() # maybe it was already open
        return

    sys.stdout.write("reading...\n")
    sys.stdout.flush()
    try:
        ser.write(b'\x7d\x81\xa1\x80\x80\x80\x80\x80\x80')
    except Exception as ex:
        print(ex)
        ser.close()
        do_alarm(0, 0, alarm_pause)  # kill alarm
        return
    while True:
        try:
            raw = ser.read(9)
        except Exception as ex:
            print(ex)
            ser.close()
            do_alarm(0, 0, alarm_pause)  # kill alarm
            return
        process_raw(raw)
        if len(raw) <= 1:
            print("no data received. Is the device on?")
            break
    ser.close()
    do_alarm(0, 0, alarm_pause)  # kill alarm

# ------------------------------------------------
in_heartbeat = False
last_beat_time = False
vibrating=-1
def new_beat():
    beat = {'interval': [], 'finger_out': [], 'searching': [], 'ok': [], 'heartbeat': [], 'strange_bits': [],
        'pulse_waveform': [], 'something_waveform': [], 'pulse_rate': [], 'SpO2': [],
        'pulse_max':[],'pulse_avg':[],'pulse_min':[], 'something_max':[],'something_avg':[],'something_min':[]}
    return beat
beat=new_beat() # contains data for 1 heartbeat

def process_raw(raw):
    global beat, last_beat_time

    if len(raw) < 9: return

    now = datetime.datetime.now()
    #print str(now), bin(ord(raw[1])), bin(ord(raw[2])), ord(raw[3]) & 0x7f, ord(raw[4]) & 0x7f, ord(raw[5]) & 0x7f, ord(raw[6]) & 0x7f, ord(raw[7]) & 0x7f, ord(raw[8]) & 0x7f # debug line
    beat["finger_out"] = bool(ord(raw[1]) & 0x1)
    beat["searching"] = bool(ord(raw[1]) & 0x2)
    beat["ok"] = not(bool((ord(raw[1]) & 0x3)))
    beat["heartbeat"] =bool(ord(raw[2]) & 0x40)
    beat["strange_bits"] = ord(raw[2]) & 0x3
    beat["pulse_waveform"].append(ord(raw[3]) & 0x7f)
    beat["something_waveform"].append(ord(raw[4]) & 0x7f)  # not sure about this
    beat["pulse_rate"] = ord(raw[5]) & 0x7f
    beat["SpO2"] = ord(raw[6]) & 0x7f
    # for some reason the heartbeat marker appears in 2 data frames!
    global in_heartbeat
    beat["heartbeat"] = beat["heartbeat"] and not in_heartbeat
    in_heartbeat=beat["heartbeat"]
    # print beat["finger_out"],beat["searching"],beat["ok"]
    if not beat["ok"] :
        last_beat_time = False
        do_alarm(0,0,alarm_pause) # kill alarm

    if in_heartbeat:
        if not last_beat_time:
            last_beat_time = now
        beat["interval"] = (now - last_beat_time).total_seconds()
        process_beat(beat)
        last_beat_time=now
        beat = new_beat()

# ------------------------------------------------
def process_beat(beat):
    p = beat["pulse_waveform"]
    beat["pulse_max"] = max(p)
    beat["pulse_min"] = min(p)
    beat["pulse_avg"] = round(float(sum(p))/len(p),1)
    p = beat["something_waveform"]
    beat["something_max"] = max(p)
    beat["something_min"] = min(p)
    beat["something_avg"] = round(float(sum(p))/len(p),1)
    print "%.3f"%(beat["interval"]), '\t', beat["SpO2"], beat["pulse_rate"], '\t(', beat["pulse_max"], beat["pulse_avg"], beat["pulse_min"], ')', '\t(',beat["something_max"], beat["something_avg"], beat["something_min"], ')'
    alarm(beat)
    write_beat(beat)

# ------------------------------------------------
def write_beat(beat):
    if not output or beat["interval"]==0:
        return
    fieldnames=['interval','SpO2', 'pulse_rate', 'pulse_max', 'pulse_avg', 'pulse_min', 'something_max', 'something_avg', 'something_min']
    to_write= { fieldname: beat[fieldname] for fieldname in fieldnames}
    with open(outfile, mode='a') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
#        writer.writeheader() # not with append
        writer.writerow(to_write)

# ------------------------------------------------
def alarm(info):
    if info["ok"] == False:
        do_alarm(0,0,alarm_pause) # kill alarm
        return
    vibrate=float(alarm_min_SpO2-info["SpO2"])/5
    vibrate=min([vibrate, 2])
    vibrate = max([vibrate, 0])
    do_alarm(vibrate,0,alarm_pause)

# ------------------------------------------------
def do_alarm(vibrate,beep,pause):
    global vibrating
    if vibrate == vibrating:
        return
    buf = '{"tremer":"%.1f", "apitar":"%.1f", "pausa":"%d"}' % (vibrate, beep, pause)
    print buf
    try:
        f=open(commandfile_path + "/comando.json","w")
        f.write(buf)
        f.close
        vibrating = vibrate
    except Exception as ex:
        print ex


################
##### Main #####
################
signal.signal(signal.SIGINT, signal_handler)
do_alarm(0,0,alarm_pause) # reset alarm
configure_serial(ser)
while 1:
    data = main_loop(ser)
    time.sleep(3) # retry in case of error

