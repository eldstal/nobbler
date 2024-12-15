import asyncio


# Send desired config change
# Send data received from a knob
Q_KNOB = None

# Send desired action to perform
Q_ACTION = None


async def init():
  global Q_KNOB
  Q_KNOB = asyncio.Queue()

  global Q_ACTION
  Q_ACTION = asyncio.Queue()

#
# Send a command to change a knob's
# configuration. If no knob is named,
# will update all connected knobs
#
async def set_config(config_name, knob=None):
  cmd = { "cmd": "config", "config": config_name, "knob": knob }
  await Q_KNOB.put(cmd)


#
# Perform a configured action
# Knob data is included, because
# the action may have to do scaling
#
async def do_action(action_name, delta, current_value, min_value, max_value):
  cmd = {
          "action": action_name,
          "delta": delta,
          "value": current_value,
          "min": min_value,
          "max": max_value
        }
  await Q_ACTION.put(cmd)