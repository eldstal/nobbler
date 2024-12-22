import asyncio
import math
import os

import command

async def rescale(action_config, command):
  # No rescaling configured for this action
  # Just return raw values
  if "scaling" not in action_config:
    return command["value"], command["min"], command["max"]

  s_min = action_config["scaling"][0]
  s_max = action_config["scaling"][1]

  relative = (command["value"] - command["min"]) / (command["max"] - command["min"])

  absolute = relative * (s_max - s_min) + s_min

  return absolute, s_min, s_max


async def perform_action(source_knob_id, action_config, received_cmd):

  placeholder = action_config.get("placeholder", "{value}")
  do_round = action_config.get("round", False)

  scaled_value, range_min, range_max = await rescale(action_config, received_cmd)

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
      print("Invoking system command:  " + cmdline)

      # TODO: Fork?
      os.system(cmdline)

    elif action_kind == "view":
      # If a knob was specified, apply it to that
      # If not, use the knob that invoked the action
      knob_id = step.get("knob", received_cmd["knob_id"])
      # TODO: Knob name translation

      new_view = step.get("view", None)
      if not new_view:
        print(f"Unable to find knob view \"{new_view}\"")
        return

      await command.set_view(new_view, knob_id)

async def main(app_config):

  verbose = app_config["nobbler"]["verbose"]

  actions = {}

  for a in app_config["actions"]:
    actions[a["name"]] = a

  while True:
    try:
      cmd = await command.Q_ACTION.get()

      if cmd["action"] not in actions:
        print(f"Tried to perform unknown action \"{cmd['action']}\". Check your configuration.")
        continue

      if (verbose): print("Performing action: " + str(cmd["action"]))

      await perform_action(cmd["knob_id"], actions[cmd["action"]], cmd)

    except asyncio.CancelledError:
      print("Terminating action task.")
      break
