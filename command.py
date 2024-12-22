import queue


# Send desired config change
# Send data received from a knob
Q_KNOB = None

# Used by different trigger sources to
# awaken the Trigger task
Q_TRIGGER = None

# Send desired action to perform
Q_ACTION = None



def init():
  global Q_KNOB
  Q_KNOB = queue.Queue()

  global Q_ACTION
  Q_ACTION = queue.Queue()

  global Q_TRIGGER
  Q_TRIGGER = queue.Queue()

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
          "knob_id": knob_id,
          "action": action_name,
          "delta": delta,
          "value": current_value,
          "min": min_value,
          "max": max_value
        }
  Q_ACTION.put(cmd)


def stop_knob():
  Q_KNOB.put(None)

def stop_trigger():
  Q_TRIGGER.put(None)

def stop_action():
  Q_ACTION.put(None)