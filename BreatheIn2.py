#!/usr/bin/env python2

# derived from:
# https://www.snip2code.com/Snippet/1802729/Read-live-data-from-a-CMS50D--pulse-oxim
#
# Copyright (c) 2018-20  celiponcio <celiponcio1@sapo.pt>
# License: GPLv2
from __future__ import print_function

import argparse
import datetime
import select
import signal
import sys
import termios
import time
import tty

import matplotlib.pyplot as plt  # compatible with matplotlib 1.1
import numpy as np
from playsound import playsound

from cms50Dplus_thread import CMS
from vibrate import Vibrate

######################
##### Parameters #####
######################

parser = argparse.ArgumentParser(
    description="Download live data from a CMS50D+ oximeter. Store at every heart beat with time.", \
    epilog="Commands: x = alarm off; space = toggle alarm on/pause (pause = 15 minutes); w = test vibration+beep (if alarm on); q or ctrl-c = quit; cvbnm = min SP02-1%; fghjk = min SP02+1%; arrow-up: beginning of the time plot; arrow-down: beginning of the time plot; arrow-left: 1h back in time; arrow-right: 1h forward in time;")
parser.add_argument('-a', '--alarm_min_SpO2', type=int, help='SpO2 minimal level. Default = 93', default=93,
                    required=False)
parser.add_argument('-d', '--device', type=str, help='path to CMS device. Example: /dev/ttyUSB0 (default)',
                    default='/dev/ttyUSB0', required=False)
parser.add_argument('-o', '--output', action='store_true', default=False)
parser.add_argument('-m', '--macAddress', type=str,
                    help='(bluetooth) mac Address of vibrator smartphone. Example E0:48:D3:C2:39:83. Default None',
                    required=False, default=None)
args = parser.parse_args()

alarm_min_SpO2 = args.alarm_min_SpO2
device = args.device
output = args.output
macAddress = args.macAddress
print(alarm_min_SpO2, device, output, macAddress)

alarm_min_PR = 45  # Extra systols! Misses ~half of the heartbeats.
# see vib.signals for specific event vibes

closing = False
vibrating = [False] * 1
cms, vib, btt, nbc = [None] * 4  # class names to be inited later
check_cms_disconnection_count = 0
loop_time = 0
alarm_flip_time = None # None = permanent alarm off
alarm_off_interval = 15*60

###################
##### Helpers #####
###################

def signal_handler(sig, frame):
    global closing
    if closing: return
    closing = True
    print('You pressed Ctrl+C! Please wait.')
    nbc.stop()  # restore normal terminal
    try:
        global vib
        vib.stop()
    except:
        pass
    try:
        global cms
        cms.stop()
    except:
        pass
    # try:
    #     global btt
    #     del btt  # stop and disconnect
    # except: pass
    sys.exit(0)


def handle_close(evt):
    signal_handler(0, 0)


def handle_press(event):
    global vib
    print('press', event.key)
    sys.stdout.flush()
    if event.key == "ctrl+c": signal_handler(0, 0)
    proc_key(event.key)


###################
##### Classes #####
###################

class NonBlockingConsole(object):

    def __init__(self):
        self.old_settings = termios.tcgetattr(sys.stdin.fileno())
        new_term = termios.tcgetattr(sys.stdin)
        new_term[3] = (new_term[3] & ~termios.ICANON & ~termios.ECHO)
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, new_term)
        tty.setcbreak(sys.stdin.fileno())

    def __del__(self):
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, self.old_settings)

    def stop(self):
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.old_settings)

    def get_data(self):
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return False


class plot(object):
    font_main = {'family': 'sans-serif',
                 'color': 'black',
                 'weight': 'normal',
                 'size': 80,
                 }
    tic = False
    SpO2avg = 0;
    SpO2avg1h = 0
    buf_size = 10 * 3600 / 2  # 10h updated avery 2 s

    # plt.style.use('dark_background') # not on matplotlib 1.1. do it by hand
    fig, ax1 = plt.subplots()
    fig.canvas.mpl_connect('close_event', handle_close)
    fig.canvas.mpl_connect('key_press_event', handle_press)
    fig.canvas.mpl_connect('button_press_event', handle_press)
    ax_pos = [0.1, 0.1, 0.8, 0.7]  #
    ax1.set_position(ax_pos, which='both')
    ax1.grid(True)
    ax1.set(xlabel='minutes', ylabel='SpO2 %')

    ax1.yaxis.label.set_color('blue')
    # fig.patch.set_facecolor('black')
    # ax1.yaxis.label.set_color('xkcd:light blue')
    # ax1.set_facecolor('black')
    # ax1.spines["bottom"].set_color('white')
    # ax1.spines["top"].set_color('white')
    # ax1.spines["left"].set_color('white')
    # ax1.spines["right"].set_color('white')
    # ax1.tick_params(axis='x', colors='white')
    # ax1.tick_params(axis='y', colors='white')

    SpO2buf = np.ones(buf_size) * 100
    #    t = np.linspace(0,buf_size-2, num=buf_size)/60*2
    #    plt.xlim((0, t.max()*1.000))
    t = np.linspace(-(buf_size - 2), 0, num=buf_size) / 60 * 2
    #    plt.xlim((t.min()*1.000),0) # full
    plt.xlim(-120, 0)
    plt.ylim((89, 99))
    # line1, = ax1.plot(t,SpO2buf, 'xkcd:light blue', linewidth=2.0)
    line1, = ax1.plot(t, SpO2buf, 'blue', linewidth=2.0)
    line1b, = ax1.plot([t.min(), 0], [alarm_min_SpO2, alarm_min_SpO2], 'r', linewidth=2.0)
    txt_main = fig.text(0.01, ax_pos[1] + ax_pos[3], '0 0', fontdict=font_main)
    txt_debug = fig.text(0.98, 0.98, 'de\nbug', verticalalignment='top', horizontalalignment='right')

    ax2 = ax1.twinx()
    ax2.set_position(ax_pos, which='both')
    ax2.set(ylabel='bpm')
    ax2.yaxis.label.set_color('green')
    # ax2.yaxis.label.set_color('xkcd:light green')
    # ax2.spines["bottom"].set_color('white') # likelly there is much more elegant way to do this
    # ax2.spines["top"].set_color('white')
    # ax2.spines["left"].set_color('white')
    # ax2.spines["right"].set_color('white')
    # ax2.tick_params(axis='x', colors='white')
    # ax2.tick_params(axis='y', colors='white')

    ax2.plot([t.min(), 0], [alarm_min_PR, alarm_min_PR], 'y', linewidth=1.0)
    PRbuf = np.ones(buf_size) * 39
    plt.ylim((40, 140))
    # line2, = ax2.plot(t,PRbuf, 'xkcd:light green', linewidth=2.0)
    line2, = ax2.plot(t, PRbuf, 'green', linewidth=2.0)
    #    ax2.plot([0, PRbuf.shape[0]], [alarm_min_air / 100 * 2 + 92 for i in range(2)], '--r', linewidth=2.0)
    plt.xlim(-120, 0)

    def update(self, **keywords):
        if closing: return

        if "adddata" in keywords:
            self.tic = not self.tic

            self.SpO2buf = np.roll(self.SpO2buf, -1)
            self.SpO2buf[-1] = cms.oldbeat.SpO2
            x = self.SpO2buf.copy()
            x[x >= 100] = None
            I = x > 0  # not nan
            if any(I): self.SpO2avg = x[I].mean()
            x = x[-1800:]  # last hour
            I = x > 0
            if any(I): self.SpO2avg1h = x[I].mean()

            self.line1.set_ydata(self.SpO2buf)

            self.PRbuf = np.roll(self.PRbuf, -1)
            self.PRbuf[-1] = cms.oldbeat.PR
            self.line2.set_ydata(self.PRbuf)

        self.txt_debug.set_text(
            '%1.1f\n%d' % (
                loop_time,
                len(cms.oldbeat.pulse_waveform)
            )
        )
        """
        s='%d%s%d%s%s<%1.1f,%1.1f>' % (
            cms.oldbeat.SpO2,
            ' :'[self.tic],
            cms.oldbeat.PR,
            ' *'[bool(vibrating)],
            ' "'[bool(cms.oldbeat.lagging)],
            self.SpO2avg-90,
            self.SpO2avg1h-90
            )
	"""
        if vib.veto and alarm_flip_time: # alarm veto on
            s = '%d%s%d%s%s[%1.0f,%1.0f](%d)' % (
                cms.oldbeat.SpO2,
                ' :'[self.tic],
                cms.oldbeat.PR,
                ' *'[bool(vibrating)],
                ' "'[bool(cms.oldbeat.lagging)],
                alarm_min_SpO2,
                alarm_min_PR,
                alarm_off_interval - (time.time() - alarm_flip_time))
        else:
            s = '%d%s%d%s%s[%1.0f,%1.0f]' % (
                cms.oldbeat.SpO2,
                ' :'[self.tic],
                cms.oldbeat.PR,
                ' *'[bool(vibrating)],
                ' "'[bool(cms.oldbeat.lagging)],
                alarm_min_SpO2,
                alarm_min_PR)

        if cms.oldbeat.SpO2 == 100:       s = 'no data'
        #        if check_cms_disconnection_count: s = 'disconnected'
        if not cms.running():             s = 'disconnected'
        if cms.beat.finger_out:           s = 'finger out'
        if cms.beat.searching:            s = 'searching'
        # self.txt_main.set_text('%s%s' % (' :'[self.tic],s))
        self.txt_main.set_text(s)
        # self.txt.set_color('xkcd:sky blue')
        # if check_cms_disconnection_count: self.txt.set_color('gray')
        # if vib.veto: self.txt.set_color('white')
        self.txt_main.set_color('blue')
        if alarm_status() == 1: self.txt_main.set_color('#ac4f06')  # temporary alarm off (xkcd:cinnamon)
        if alarm_status() == 2: self.txt_main.set_color('black')  # permanent alarm off
        if not vib.running(): self.txt_main.set_color('red')  # no vibes

        self.line1b.set_ydata([alarm_min_SpO2, alarm_min_SpO2])

        plt.draw()  # very slow operation
        plt.pause(0.001)

    def scroll(self, key):
        if key == 'left':
            v = [x - 60 for x in plt.xlim()]
            if v[0] < -600: v = [-600, -480]
            plt.xlim(v[0], v[1])
        if key == 'right':
            v = [x + 60 for x in plt.xlim()]
            if v[1] > 0: v = [-120, -0]
            plt.xlim(v[0], v[1])
        if key == 'down':
            plt.xlim(-120, 0)
        if key == 'up':
            plt.xlim(-600, -480)


#####################
##### Functions #####
#####################

def beep():
    if alarm_status() == 2: return  # do not play if permanent alarm off
    try:
        playsound('beep-08b.mp3')
    except Exception as ex:
        # print(str(ex))
        print("bip, bip")


def check_vib_disconnection():
    if not vib.veto and not vib.running():
        beep()


def check_cms_disconnection():
    global check_cms_disconnection_count
    if vib.veto or cms.running():
        check_cms_disconnection_count = 0
        return False
    check_cms_disconnection_count += 1
    if check_cms_disconnection_count == 1:
        if not cms.beat.searching: vib.vibrate(vib.signal.disconnected)
        print('cms: waiting for good data')
    elif check_cms_disconnection_count < 5:
        return  # wait 5 * 2 seconds
    else:
        if not cms.beat.searching: vib.vibrate(vib.signal.disconnected)
    return True


def alarm_off_flip(interval=15*60):
    global alarm_off_interval, alarm_flip_time
    alarm_off_interval = interval
    vib.veto = not vib.veto
    print("alarm_stop =", vib.veto)
    alarm_flip_time = time.time()


def alarm():
    global vibrating, alarm_flip_time

    if vib.veto and alarm_flip_time and \
            ((time.time() - alarm_flip_time) > alarm_off_interval):
            alarm_off_flip() # general alarm_off reset (that is, alarm on)
    if not cms.beat.finger_out:
        alarm.new_finger_out = False
    elif not alarm.new_finger_out and not vib.veto and alarm_flip_time and\
            ((time.time() - vib.last_vibration_time) < 5):
        alarm.new_finger_out = True
        alarm_off_flip(60)

    if not check_cms_disconnection_count:
        if cms.oldbeat.PR < alarm_min_PR:  # palpitations! priority
            vib.vibrate(vib.signal.PR)
            return
        vibrate = (alarm_min_SpO2 - cms.oldbeat.SpO2) * 1000 / 20  # in steps of 0.05
        vibrate = min([vibrate, 500])
        vibrate = max([vibrate, 0])
        if vibrate > 0:
            vibrating = True
        else:
            vibrating = False
        s = "%d,0,0,0,0" % vibrate
        # print(s)
        vib.vibrate(s)  # this waits for the vibration to complete


def proc_key(key): # runs at every cycle
    global alarm_min_SpO2, alarm_flip_time, vib
    if key == " ": alarm_off_flip(15 * 60)
    if not key: return
    if 'cvbnm'.find(key) >= 0:
        alarm_min_SpO2 -= 1
        print('alarm_min_SpO2 = %d' % alarm_min_SpO2)
    if 'fghjk'.find(key) >= 0:
        alarm_min_SpO2 += 1
        print('alarm_min_SpO2 = %d' % alarm_min_SpO2)
    # print(key, end=''); sys.stdout.flush()
    if key == "w":  # test beep
        tmp = vib.veto
        vib.veto = False
        vib.vibrate(vib.signal.main_dead)
        beep()
        vib.veto = tmp
    if key == "q":
        signal_handler(0, 0)
    if key == "x":
        vib.veto = True
        print("alarm_stop =", vib.veto)
        alarm_flip_time = None  # permanent alarm off
    pl.scroll(key)  # try to scroll if keys are right
    pl.update()


def alarm_status():
    if vib.veto and alarm_flip_time: return 1  # temporary off
    if vib.veto and not alarm_flip_time: return 2  # permanent off
    return 0  # on


################
##### Main #####
################

signal.signal(signal.SIGINT, signal_handler)

nbc = NonBlockingConsole()  # actually unnecessary. use instead handle_press in matplotlib

# bitalino init & start
# btt = BTT(macAddress) # this connects to bitalino
# if btt.bitalino:
#     btt.acqChannels = [0, 1]
#     btt.fifoDepth = 2 # seconds
#     btt.start()

# cms init & start
outfile = None
if output: outfile = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_BreatheIn2.csv"
print(outfile)
cms = CMS(device, outfile)
cms.verbose = 1
cms.start()

vib = Vibrate(macAddress)
vib.verbose = 1
vib._what_services()
vib.veto = True
alarm_flip_time = None  # start with alarm off. space key is needed to start

# init plot
pl = plot()
pl.update()

# main loop
while True:
    now = time.time()
    vib.main_is_alive = True  # if not set, vibrates thrice

    # print('1',end=''); sys.stdout.flush()

    try:
        key = nbc.get_data()
    except:
        key = None
    proc_key(key)  # this does several things. Must be called.
    alarm()  # this waits for vibration to stop

    # print('2',end=''); sys.stdout.flush()

    check_cms_disconnection()
    # print('3',end=''); sys.stdout.flush()
    check_vib_disconnection()
    # print('4', end=''); sys.stdout.flush()

    if closing: break

    pl.update(adddata=True)
    time.sleep(max([2 - (time.time() - now), 0.001]))  # pooling rate. Increase to 2 in slow computers.

    loop_time = time.time() - now
    # print('=',loop_time); sys.stdout.flush()
