import math
import os
import subprocess
import re

import command

NOBBLER_ROOT=os.path.dirname(os.path.dirname(__file__))
NOBBLER_SCRIPTS_DIR=os.path.join(NOBBLER_ROOT, "scripts")

def _clamp(value, d_min, d_max):
  value = max(value, d_min)
  value = min(value, d_max)
  return value

def _change_range(value, s_min, s_max, d_min, d_max):
  relative = (value - s_min) / (s_max - s_min)
  absolute = relative * (d_max - d_min) + d_min

  return _clamp(absolute, d_min, d_max)

def _rescale(action_config, command):
  # No rescaling configured for this action
  # Just return raw values
  if "scaling" not in action_config:
    return command["value"], command["min"], command["max"]

  d_min = action_config["scaling"][0]
  d_max = action_config["scaling"][1]

  absolute = _change_range(command["value"], command["min"], command["max"], d_min, d_max)

  return absolute, d_min, d_max

def _run_cmd_get_output(cmdline):
  cmdline = cmdline.replace("{scripts}", NOBBLER_SCRIPTS_DIR)

  try:
    print("Invoking system command:  " + cmdline)
    output = subprocess.check_output(cmdline, timeout=1, shell=True)
    return output.decode()
  
  except subprocess.CalledProcessError as e:
    print(f"Command {cmdline} failed to execute:")
    print(output)

  except:
    pass

  return None
  

def _perform_action(source_knob_id, action_config, received_cmd):

  placeholder = action_config.get("placeholder", "{value}")
  do_round = action_config.get("round", False)

  scaled_value, range_min, range_max = _rescale(action_config, received_cmd)

  if do_round:
    scaled_value = int(round(scaled_value))


  for step in action_config["steps"]:
    action_kind = step["kind"]

    if action_kind == "log":
      msg = step["message"].replace(placeholder, str(scaled_value))
      print(msg)

    elif action_kind == "command":

      cmdline = step.get("command", None)
      if not cmdline:
        continue

      cmdline = cmdline.replace(placeholder, str(scaled_value))
      cmdline = cmdline.replace("{scripts}", NOBBLER_SCRIPTS_DIR)
      print("Invoking system command:  " + cmdline)

      # Run the command, don't wait for a result
      subprocess.Popen(cmdline, shell=True)

    elif action_kind == "view":
      # If a knob was specified, apply it to that
      # If not, use the knob that invoked the action
      knob_id = step.get("knob", received_cmd["knob_id"])
      # TODO: Knob name translation

      new_view = step.get("view", None)
      if not new_view:
        print(f"Unable to find knob view \"{new_view}\"")
        return

      command.set_view(new_view, knob_id)

def _get_action_value(action, d_min, d_max):
      # Not an action we know
      if not action:
        return None

      cmdline = action.get("get_command", None)

      # Action doesn't have a command configured
      if not cmdline:
        return None
      
      output = _run_cmd_get_output(cmdline)
      if not output:
        return None

      # Just find the first number-alike in the output.
      matches = re.match("((-?)[0-9]+(\.[0-9]+)?)", output)

      if not matches:
        print(f"Failed to parse output of command {cmdline}")
        print(output)
        return None

      value = float(matches[0])

      scaling = action.get("scaling", None)
      if scaling:
        value = _change_range(value, scaling[0], scaling[1], d_min, d_max)
      else:
        value = _clamp(value, d_min, d_max)

      return value

def main(app_config):

  verbose = app_config["nobbler"]["verbose"]

  actions = {}

  for a in app_config["actions"]:
    actions[a["name"]] = a

  while True:
    cmd = command.Q_ACTION.get()

    if cmd is None:
      print("Terminating action task.")
      break

    if cmd["cmd"] == "do_action":
      if cmd["action"] not in actions:
        print(f"Tried to perform unknown action \"{cmd['action']}\". Check your configuration.")
        continue

      if (verbose): print("Performing action: " + str(cmd["action"]))

      _perform_action(cmd["knob_id"], actions[cmd["action"]], cmd)

    elif cmd["cmd"] == "get_action_value":
      # Run a getter command to find the current value.
      # this will be set on the knob so that the knob display corresponds with reality

      callback = cmd["callback"]
      action = actions.get(cmd["action"], None)
      output = _get_action_value(action, cmd["min"], cmd["max"])

      callback(output)
