import asyncio

import command

def rescale(action_config, command):
  # No rescaling configured for this action
  # Just return raw values
  if "scaling" not in action_config:
    return command["value"], command["min"], command["max"]

  s_min = action_config["scaling"][0]
  s_max = action_config["scaling"][1]

  relative = (command["value"] - command["min"]) / (command["max"] - command["min"])

  absolute = relative * (s_max - s_min) + s_min

  return int(round(absolute)), s_min, s_max


async def perform_action(action_config, command):
  scaled_value, range_min, range_max = rescale(action_config, command)

  placeholder = action_config.get("placeholder", "{value}")

  for action_type, action in action_config["actions"].items():
    if action_type == "log":
      msg = action["message"].replace(placeholder, str(scaled_value))
      print(msg)

    elif action_config["type"] == "command":
      pass

async def main(config):

  actions = {}

  for a in config["actions"]:
    actions[a["name"]] = a

  print("Action task started.")

  while True:
    try:
      cmd = await command.Q_ACTION.get()
      print("Action task got " + str(cmd))

      if cmd["action"] not in actions:
        print(f"Tried to perform unknown action \"{action}\". Check your configuration.")
        continue

      await perform_action(actions[cmd["action"]], cmd)

    except asyncio.CancelledError:
      print("Terminating action task.")
      break
