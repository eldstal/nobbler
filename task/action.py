import asyncio
import math

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

  return int(round(absolute)), s_min, s_max


async def perform_action(source_knob_id, action_config, received_cmd):
  scaled_value, range_min, range_max = await rescale(action_config, received_cmd)

  placeholder = action_config.get("placeholder", "{value}")

  for action_type, action in action_config["actions"].items():
    if action_type == "log":
      msg = action["message"].replace(placeholder, str(scaled_value))
      print(msg)

    elif action_type == "command":
      pass

    elif action_type == "config":
      # If a knob was specified, apply it to that
      # If not, use the knob that invoked the action
      knob_id = action.get("knob", received_cmd["knob_id"])
      # TODO: Knob name translation

      new_knob_conf = action.get("config", None)
      if not new_knob_conf:
        print(f"Unable to find knob config \"{new_knob_conf}\"")
        return

      await command.set_config(new_knob_conf, knob_id)

async def main(config):

  actions = {}

  for a in config["actions"]:
    actions[a["name"]] = a

  print("Action task started.")

  while True:
    try:
      cmd = await command.Q_ACTION.get()

      if cmd["action"] not in actions:
        print(f"Tried to perform unknown action \"{action}\". Check your configuration.")
        continue

      await perform_action(cmd["knob_id"], actions[cmd["action"]], cmd)

    except asyncio.CancelledError:
      print("Terminating action task.")
      break
