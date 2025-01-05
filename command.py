import queue
import os
import multiprocessing

import task.action
import task.state


# Send desired config change
# Send data received from a knob
Q_KNOB = None

# Used by different trigger sources to
# awaken the Trigger task
Q_TRIGGER = None

# Send desired action to perform
Q_ACTION = None

# Used to manage the polling of system information
# by actions' get_command
Q_STATE = None


def init():
  global Q_KNOB
  Q_KNOB = queue.Queue()

  global Q_ACTION
  Q_ACTION = queue.Queue()

  global Q_TRIGGER
  Q_TRIGGER = queue.Queue()

  # This needs to be a multiprocessing queue
  # because we use multiprocessing for the
  # background commands.
  global Q_STATE
  Q_STATE = multiprocessing.Queue()

#
# Send a command to change a knob's
# view (its active configuration and what we do with data).
# If no knob is named, will update all connected knobs
#
def set_view(view_name, knob=None):
  cmd = { "cmd": "view", "view": view_name, "knob": knob }
  Q_KNOB.put(cmd)


#
# Perform a configured action
# Knob data is included, because
# the action may have to do scaling
#
def do_action(knob_id, action_name, delta, current_value, min_value, max_value):
  cmd = {
          "cmd": "do_action",
          "knob_id": knob_id,
          "action": action_name,
          "delta": delta,
          "value": current_value,
          "min": min_value,
          "max": max_value
        }
  Q_ACTION.put(cmd)

#
# Fetch the result of `get_command` associated with an action
# and return the resulting value. If scaling is configured
# for the action, the value will be converted to the range
# [ v_min, v_max ]
# Returns None if no command is configured
# Returns None if the command can't be invoked
# Returns None if no output can be parsed
#
def action_get_value(action_name, v_min, v_max, allow_delay=False):
 
  value = task.state.get_value_for_action(action_name, v_min, v_max, allow_delay)

  if not value:
    return None
  
  return round(value)

def window_focused(title, appname):
  cmd = {
          "cmd": "window-focused",
          "title": title,
          "appname": appname
        }
  Q_TRIGGER.put(cmd)






def stop_knob():
  Q_KNOB.put(None)

def stop_trigger():
  Q_TRIGGER.put(None)

def stop_action():
  Q_ACTION.put(None)

def stop_state():
  Q_STATE.put(None)