import math
import argparse
import queue
import sys

from comtypes import CLSCTX_ALL, COMObject
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IAudioEndpointVolumeCallback

def win_get_control():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = interface.QueryInterface(IAudioEndpointVolume)
    return volume

def win_perc_to_vol(control, percentage):
    vol_min, vol_max, step = control.GetVolumeRange()
    if percentage > 0:
        level = 14.923111050518 * math.log(0.009964267213232 * percentage)
    else:
        level = vol_min

    level = min(level, vol_max)
    level = max(level, vol_min)
    return level

def win_vol_to_perc(control, level):
    #vol_min, vol_max, step = control.GetVolumeRange()

    # These coefficients work on my machine. Not sure if it is general windows
    # behavior, or just what is correct for my setup.
    percentage = math.e ** (level / 14.923111050518) /  0.009964267213232
    percentage = int(round(percentage))
    percentage = min(percentage, 100)
    percentage = max(percentage, 0)
    return percentage
    

def win_get_vol():

    control = win_get_control()
    level = control.GetMasterVolumeLevel()
    return win_vol_to_perc(control, level)

def win_set_vol(percentage):
    percentage = min(percentage, 100)
    percentage = max(percentage, 0)

    control = win_get_control()
    level = win_perc_to_vol(control, percentage)

    control.SetMasterVolumeLevel(level, None)


def win_watch_vol():
    control = win_get_control()
    que = queue.Queue()
    callback = VolumeCallback(que)
    control.RegisterControlChangeNotify(callback)

    # A fully blocking loop would work great,
    # but that swallows ctrl+c, so we can never quit.
    vol = -1
    while True:
        new_vol = win_get_vol()

        if new_vol != vol:
            print(new_vol)
            sys.stdout.flush()
            vol = new_vol


        try:
            que.get(timeout=0.5)
        except queue.Empty:
            continue



class VolumeCallback(COMObject):
    _com_interfaces_ = [IAudioEndpointVolumeCallback]

    def __init__(self, que):
        self.que = que

    def OnNotify(self, pNotify):
        # Be careful in here.
        # Exceptions aren't propagated,
        # so this function will just fail silently.
        self.que.put(True)




parser = argparse.ArgumentParser("Control system volume")
commands = parser.add_subparsers(dest="command", help="Command")

watch_parser = commands.add_parser("watch", help="Continuously watch volume. Output only when volume changes.")

get_parser = commands.add_parser("get", help="Get system volume (0-100)")

set_parser = commands.add_parser("set", help="Set system volume (0-100)")
set_parser.add_argument("percentage", nargs=1, type=int, help="Exact volume level to set 0 - 100, inclusive")

change_parser = commands.add_parser("change", help="Change system volume (relative)")
change_parser.add_argument("delta", nargs=1, type=int, help="Desired change in volume (relative), -100 - +100, inclusive")

conf = parser.parse_args()

if conf.command == "get":
    print(win_get_vol())
elif conf.command == "watch":
    win_watch_vol()
elif conf.command == "set":
    win_set_vol(conf.percentage[0])
elif conf.command == "change":
    current = win_get_vol()
    win_set_vol(current + conf.delta[0])