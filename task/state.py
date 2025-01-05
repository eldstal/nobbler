# A task which polls system state,
# for example the current volume or other
# things we want to display on the knob
#
# Each "get_command" specified by a configured action
# will get its own multiprocessing.process to run that
# command continuously (or periodically) and feed the
# output back to the main task. There, the value is
# stored.
#
# When we need a value (e.g. when a knob changes view)
# we can look the data up in a quick table rather than
# running the system command.
#
# Overhead: Higher.
# Latency: Lower.
#
# If a command runs continuously, each output line is treated
# as output. That way, if you don't want polling you can create
# a get_command which is event-driven.

import command
import subprocess
import time
import multiprocessing
import threading
import re

from task.action import NOBBLER_SCRIPTS_DIR

_ALL_ACTIONS = {}

_RAW_VALUES_LOCK = threading.Lock()
_RAW_VALUES = {}

def _clamp(value, d_min, d_max):
  value = max(value, d_min)
  value = min(value, d_max)
  return value

def _change_range(value, s_min, s_max, d_min, d_max):
  relative = (value - s_min) / (s_max - s_min)
  absolute = relative * (d_max - d_min) + d_min

  return _clamp(absolute, d_min, d_max)

def _get_value_from_output(output):
    if not output:
        return None

    # Just find the first number-alike in the output.
    matches = re.match("((-?)[0-9]+(\.[0-9]+)?)", output)

    if not matches:
        print(f"Failed to parse output of command:")
        print(output)
        return None

    value = float(matches[0])
    return value



#
# Body of a multiprocessing.process which continously
# runs a command and feeds the result back
#
def _proc_action_cmd(cmdline, action_name, queue):
    cmdline = cmdline.replace("{scripts}", NOBBLER_SCRIPTS_DIR)
    while True:

        # TODO: Configurable polling rate
        time.sleep(1)

        try:
            # TODO: Continuously read data from command output
            output = subprocess.check_output(cmdline, timeout=1, shell=True)

            if not output:
                continue

            value = _get_value_from_output(output.decode())

            if not value:
                continue

            # Send the value back to the mother thread
            queue.put({
                "cmd": "value",
                "action": action_name,
                "value": value
            })

        
        except subprocess.CalledProcessError as e:
            print(f"Command {cmdline} failed to execute:")
            print(output)

        except:
            pass


def get_value_for_action(action_name, range_min, range_max, allow_delay=False):
    # Someone has asked for a recent value
    # Let's just look it up in our table and be done with it

    action = _ALL_ACTIONS.get(action_name, None)
    if not action:
        return None

    # Boot-up hack
    # If we still haven't gotten any values after starting up,
    # just delay this command a bit. It'll be OK.
    if allow_delay:
        for wait_tick in range(10):
            need_wait = False
            with _RAW_VALUES_LOCK:
                if ("get_command" in action and action_name not in _RAW_VALUES):
                    need_wait = True

            if need_wait:
                print(f"No known value for {action_name} yet. Delaying.")
                time.sleep(0.1)
            else:
                break


    # The raw value received from the background process
    with _RAW_VALUES_LOCK:
        raw_value = _RAW_VALUES.get(action_name, None)

    if not raw_value:
        return None          


    # If the action has scaling configured, we need to
    # re-scale to fit the range of the caller
    # For example, our command outputs [0, 65535] but the
    # knob is set up for [0, 100]

    scaling = action.get("scaling", None)
    if scaling:
        clean_value = _change_range(raw_value, scaling[0], scaling[1], range_min, range_max)
    else:
        clean_value = _clamp(raw_value, range_min, range_max)


    return clean_value



def main(app_config):

    processes = []

    for a in app_config["actions"]:
        _ALL_ACTIONS[a["name"]] = a


    for action_name, action in _ALL_ACTIONS.items():
        cmdline = action.get("get_command", None)

        if not cmdline: continue

        process = multiprocessing.Process(target=_proc_action_cmd, args=(cmdline, action_name, command.Q_STATE))
        process.start()
        processes.append(process)


    while True:
        cmd = command.Q_STATE.get()

        if cmd is None:
            print("Terminating action task.")
            break

        print(cmd)

        # We've received an updated value from a background process
        if cmd["cmd"] == "value":
            with _RAW_VALUES_LOCK:
                _RAW_VALUES[cmd["action"]] = cmd["value"]



    for p in processes:
        p.terminate()
