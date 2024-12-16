import asyncio
import math
from queue import Queue
import functools
import serial
import serial.tools.list_ports

import command

from smartknob_io.smartknob_io import (
    Smartknob,
    SMARTKNOB_BAUD
)
from smartknob_io.proto_gen import smartknob_pb2

# The standard python lib for smarknob
# provides a handler object which
# starts two threads for the knob.
# We need to keep track of these to be able
# to shut down cleanly.
# Each entry is an object of
#  handler
#  prev_position
#  position_nonce
#  press_nonce
KNOB_CONNECTION = {}


def get_serial_port(portname):

    ports = sorted(
        filter(
            lambda p: p.description != 'n/a',
            serial.tools.list_ports.comports(),
        ),
        key=lambda p: p.device,
    )

    for p in ports:
      if p.device == portname:
        print(f"Connecting to serial port {p.device}")
        return serial.Serial(p.device, SMARTKNOB_BAUD, timeout=1.0)

    return None

def start_serial(portname):
  port = get_serial_port(portname)
  if not port: return None

  s = Smartknob(port)
  s.start()

  s._logger.info('Connecting to smartknob...')
  q = Queue(1)

  def startup_handler(message):
      try:
          q.put_nowait(message)
      except Full:
          pass
  unregister = s.add_handler('smartknob_state', startup_handler)

  s.request_state()
  first_message = q.get()
  unregister()
  s._logger.info('Connected!')

  return s, first_message


def message_from_knob(queue, knob_id, message_type, message):
  #loop.call_soon_threadsafe(command.new_data, knob_id, message_type, message)
  cmd = { "cmd": "data", "knob_id": knob_id, "message_type": message_type, "message": message }
  queue.put_nowait(cmd)
  #loop.create_task(command.new_data(knob_id, message_type, message))
  #loop.run_until_complete(command.new_data(knob_id, message_type, message))


async def handle_data(knob_id, msg):
  state = KNOB_CONNECTION[knob_id]
  current_config = state.get("current_config", None)

  if msg.press_nonce != state["press_nonce"]:
    state["press_nonce"] = msg.press_nonce
    KNOB_CONNECTION[knob_id] = state

    if current_config:
      if "press_action" in current_config:
        await command.do_action(
                          knob_id,
                          current_config["press_action"],
                          1,
                          1,
                          0,
                          1
                      )

    # TODO: Pass the press on to the trigger task
    # in case there's a generic button press trigger

    return

  elif msg.current_position != state["prev_position"]:
    delta = msg.current_position - state["prev_position"]
    state["prev_position"] = msg.current_position
    KNOB_CONNECTION[knob_id] = state

    if current_config:
      if "knob_action" in current_config:
        await command.do_action(
                          knob_id,
                          current_config["knob_action"],
                          delta,
                          msg.current_position,
                          msg.config.min_position,
                          msg.config.max_position
                      )


async def apply_knob_config(knob_id, new_config):
  state = KNOB_CONNECTION.get(knob_id, None)
  if not state:
    print(f"Unable to update configuration for unknown knob {knob_id}.")
    return

  handler = state["handler"]

  # The knob's parameters
  new_knob_config = new_config["config"]

  config = smartknob_pb2.SmartKnobConfig()
  config.position = new_knob_config.get("position", 0)
  config.min_position = new_knob_config.get("min_position", 0)
  config.max_position = new_knob_config.get("max_position", 5)
  config.position_width_radians = new_knob_config.get("position_width_radians", math.radians(10))
  config.detent_strength_unit = new_knob_config.get("detent_strength_unit", 1)
  config.endstop_strength_unit = new_knob_config.get("endstop_strength_unit", 1)
  config.snap_point = new_knob_config.get("snap_point", 1.1)
  config.text = new_knob_config.get("text", "NO TEXT CONFIGURED!!")
  config.led_hue = new_knob_config.get("led_hue", 0)
  handler.set_config(config)

  # Other settings like actions etc.
  state["current_config"] = new_config
  KNOB_CONNECTION[knob_id] = state

async def main(app_config):

  # TODO: Configurable startup config
  default_config = app_config["configs"][0]

  knob_configs = {}
  for c in app_config["configs"]:
    knob_configs[c["name"]] = c

  for i in app_config["knobs"]["interfaces"]:
    if i["type"] == "serial":
      portname = i["device"]

      # TODO: Get unique ID from knob
      knob_id = portname

      handler, first_status = start_serial(portname)
      if handler:
        KNOB_CONNECTION[knob_id] = {
            "handler": handler,
            "prev_position": first_status.current_position,
            "position_nonce": first_status.config.position_nonce,
            "press_nonce": first_status.press_nonce,
            "current_config": default_config
          }

        for message_type in [ "smartknob_state" ]:
          # Messy little workaround to get the standard (non-asyncio)
          # handler's event into our own loop
          handler.add_handler(message_type, functools.partial(message_from_knob,
            command.Q_KNOB,
            knob_id,
            message_type)
          )

        # Give the knob a startup configuration
        await apply_knob_config(knob_id, KNOB_CONNECTION[knob_id]["current_config"])

      else:
        print(f"Couldn't find a knob on {portname}...")

  print(f"Started communications with {len(KNOB_CONNECTION)} knob(s).")

  while True:
    try:
      cmd = await command.Q_KNOB.get()
      #print("Knob task got: " + str(cmd))

      if cmd["cmd"] == "config":
        # Someone has requested a configuration change for a knob

        new_knob_config = knob_configs.get(cmd["config"], None)

        if not new_knob_config:
          print(f"Unable to find knob configuration {cmd['config']}. Check your app configuration.")
          continue

        # By default, apply to all knobs
        knob_ids = list(KNOB_CONNECTION.keys())

        # If one is specified, apply to that one
        if "knob" in cmd and cmd["knob"]:
          knob_ids = [ cmd["knob"] ]
          # TODO: Knob name translation

        for knob_id in knob_ids:
          await apply_knob_config(knob_id, new_knob_config)

      elif cmd["cmd"] == "data":
        # Data has arrived from a knob
        #print(f"Message[{cmd['knob_id']}] ({cmd['message_type']}): {cmd['message']}")

        knob_id = cmd["knob_id"]
        msg = cmd["message"]

        if knob_id in KNOB_CONNECTION:
          await handle_data(knob_id, msg)
          continue

    except asyncio.CancelledError:
      print("Terminating knob task.")
      break


  for name, state in KNOB_CONNECTION.items():
    try:
      state["handler"].shutdown()
    except:
      pass
