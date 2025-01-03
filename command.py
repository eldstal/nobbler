import queue
import os

import task.action


# Send desired config change
# Send data received from a knob
Q_KNOB = None

# Used by different trigger sources to
# awaken the Trigger task
Q_TRIGGER = None

# Send desired action to perform
Q_ACTION = None



def _update_command_path():
  approot = os.path.dirname(__file__)
  scriptdir = os.path.join(approot, "scripts")
  if not os.path.isdir(scriptdir): return

  if "PATH" not in os.environ: return

  os.environ["PATH"] += os.pathsep + scriptdir
  print("Added Nobbler scripts to PATH. PATH is now =" + os.environ["PATH"])

def init():
  global Q_KNOB
  Q_KNOB = queue.Queue()

  global Q_ACTION
  Q_ACTION = queue.Queue()

  global Q_TRIGGER
  Q_TRIGGER = queue.Queue()

  #_update_command_path()

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
# Run the `get_command` associated with an action
# and return the resulting value. If scaling is configured
# for the action, the value will be converted to the range
# [ v_min, v_max ]
# Returns None if no command is configured
# Returns None if the command can't be invoked
# Returns None if no output can be parsed
#
def action_get_value(action_name, v_min, v_max):
  q_response = queue.Queue()
  cmd = {
    "cmd": "get_action_value",
    "action": action_name,
    "min": v_min,
    "max": v_max,
    "callback": q_response.put
  }
  Q_ACTION.put(cmd)

  try:
    result = q_response.get(timeout=1)
  except queue.Empty:
    print("get_command for action {action_name} timed out. Won't set knob value.")

  if not result:
    return None
  
  return round(result)

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