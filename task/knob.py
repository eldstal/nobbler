import asyncio
from queue import Queue
import functools
import serial
import serial.tools.list_ports

import command

from smartknob_io.smartknob_io import (
    Smartknob,
    SMARTKNOB_BAUD
)

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

  if msg.press_nonce != state["press_nonce"]:
    state["press_nonce"] = msg.press_nonce
    KNOB_CONNECTION[knob_id] = state

    # TODO: press_action action from current config

    # TODO: Pass the press on to the trigger task
    # in case there's a generic button press trigger

    await command.do_action("debug",
                      delta,
                      1,
                      0,
                      1
                      )
    return

  elif msg.current_position != state["prev_position"]:
    delta = msg.current_position - state["prev_position"]
    state["prev_position"] = msg.current_position
    KNOB_CONNECTION[knob_id] = state

    # TODO: knob_action from current config

    await command.do_action("debug",
                      delta,
                      msg.current_position,
                      msg.config.min_position,
                      msg.config.max_position
                      )

async def main(config):

  for i in config["knobs"]["interfaces"]:
    if i["type"] == "serial":
      portname = i["device"]

      # TODO: Get unique ID from knob
      knob_id = portname

      handler, first_status = start_serial(portname)
      print(first_status)
      if handler:
        KNOB_CONNECTION[knob_id] = {
            "handler": handler,
            "prev_position": first_status.current_position,
            "position_nonce": first_status.config.position_nonce,
            "press_nonce": first_status.press_nonce
          }

        for message_type in [ "smartknob_state" ]:
          # Messy little workaround to get the standard (non-asyncio)
          # handler's event into our own loop
          handler.add_handler(message_type, functools.partial(message_from_knob,
            command.Q_KNOB,
            knob_id,
            message_type)
          )
      else:
        print(f"Couldn't find a knob on {portname}...")

  print(f"Started communications with {len(KNOB_CONNECTION)} knob(s).")

  while True:
    try:
      cmd = await command.Q_KNOB.get()
      #print("Knob task got: " + str(cmd))

      if cmd["cmd"] == "config":
        # Someone has requested a configuration change for a knob
        print("Changing configuration.")

      elif cmd["cmd"] == "data":
        # Data has arrived from a knob
        #print(f"Message[{cmd['knob_id']}] ({cmd['message_type']}): {cmd['message']}")

        knob_id = cmd["knob_id"]
        msg = cmd["message"]

        if knob_id not in KNOB_CONNECTION:
          handle_data(knob_id, msg)
          continue

    except asyncio.CancelledError:
      print("Terminating knob task.")
      break


  for name, state in KNOB_CONNECTION.items():
    try:
      state["handler"].shutdown()
    except:
      pass
