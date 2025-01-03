import math
from queue import Queue, Full
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

# Keeps track of which physical interfaces (serial ports)
# are already in use (= have a handler in KNOB_CONNECTION)
# so we can skip them during auto-configuration
KNOB_INTERFACES = {}

#
# Find the first serial port that identifies as the CH340
#
def get_serial_port_auto():
  ports = sorted(
      filter(
          lambda p: p.description != 'n/a',
          serial.tools.list_ports.comports(),
      ),
      key=lambda p: p.device,
  )

  for p in ports:

    # Don't pick a port that we've already configured
    if p.device in KNOB_INTERFACES:
      continue

    if "USB-SERIAL CH340" in p.description:
      print(f"Auto-connecting to serial port {p.device}")
      return p.device, serial.Serial(p.device, SMARTKNOB_BAUD, timeout=1.0)

  print("No more knobs found for auto-configuration. Specify a serial port or connect another smartknob.")
  return None, None
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

  if portname:
    port = get_serial_port(portname)
  else:
    # Auto-select the first port that looks OK
    portname, port = get_serial_port_auto()

  if not port: return None, None, None

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

  return portname, s, first_message


def message_from_knob(queue, knob_id, message_type, message):
  

  state = KNOB_CONNECTION[knob_id]


  # We will get -lots- of updates from the knob,
  # since the subposition value jitters.
  # We don't care about those and don't want those events
  # clogging up the event queue slowing down the handling,
  # so we skip them here.

  if message_type == "smartknob_state":

    compare = lambda value, key: value == state["current_view"]["config"].get(key, value)

    # TODO: This probably isn't a safe comparison.
    # floating point equality is a finnicky subject.
    # Ideally, we should have a config_nonce in the knob state.    
    config_is_same = (
      compare(message.config.min_position, "min_position") and
      compare(message.config.max_position, "max_position") and
      #compare(message.config.position_width_radians, "position_with_radians") and
      #compare(message.config.detent_strength_unit, "detent_strength_unit") and
      #compare(message.config.endstop_strength_unit, "endstop_strength_unit") and
      #compare(message.config.snap_point, "snap_point") and
      compare(message.config.text, "text") and
      compare(message.config.led_hue, "led_hue")
    )
     

    position_is_same = (message.current_position == state["prev_position"] and
                        message.press_nonce == state["press_nonce"]
                       )
    
    if config_is_same and position_is_same: return
    
  cmd = { "cmd": "data", "knob_id": knob_id, "message_type": message_type, "message": message }
  queue.put_nowait(cmd)



def handle_data(knob_id, msg):
  state = KNOB_CONNECTION[knob_id]
  current_view = state.get("current_view", None)

  if msg.press_nonce != state["press_nonce"]:
    state["press_nonce"] = msg.press_nonce
    KNOB_CONNECTION[knob_id] = state

    if current_view:
      if "press_action" in current_view:
        command.do_action(
                          knob_id,
                          current_view["press_action"],
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

    if current_view:
      if "knob_action" in current_view:
        command.do_action(
                          knob_id,
                          current_view["knob_action"],
                          delta,
                          msg.current_position,
                          msg.config.min_position,
                          msg.config.max_position
                      )


def apply_knob_view(knob_id, new_view):
  state = KNOB_CONNECTION.get(knob_id, None)
  if not state:
    print(f"Unable to update configuration for unknown knob {knob_id}.")
    return

  handler = state["handler"]

  # The knob's parameters
  new_knob_config = new_view["config"]

  initial_pos = new_knob_config.get("position", 0)
  pos_min = new_knob_config.get("min_position", 0)
  pos_max = new_knob_config.get("max_position", 5)

  # If the action has a get_command specified, we'll call that
  # to set the initial value for the view. Just you watch!
  knob_action = new_view.get("knob_action", None)
  if knob_action:
    dynamic_initial = command.action_get_value(knob_action, pos_min, pos_max)
    if dynamic_initial: initial_pos = dynamic_initial

  config = smartknob_pb2.SmartKnobConfig()
  config.position = initial_pos
  config.min_position = pos_min
  config.max_position = pos_max
  config.position_width_radians = new_knob_config.get("position_width_radians", math.radians(10))
  config.detent_strength_unit = new_knob_config.get("detent_strength_unit", 1)
  config.endstop_strength_unit = new_knob_config.get("endstop_strength_unit", 1)
  config.snap_point = new_knob_config.get("snap_point", 1.1)
  config.text = new_knob_config.get("text", "NO TEXT CONFIGURED!!")
  config.led_hue = new_knob_config.get("led_hue", 0)
  handler.set_config(config)

  # Other settings like actions etc.
  state["current_view"] = new_view
  KNOB_CONNECTION[knob_id] = state


def main(app_config):

  # TODO: Configurable startup config
  default_view = app_config["views"][0]

  verbose = app_config["nobbler"].get("verbose", False)

  knob_views = {}
  for c in app_config["views"]:
    knob_views[c["name"]] = c

  for i in app_config["knobs"]["interfaces"]:
    if i["kind"] == "serial":
      portname = i.get("device", None)

      portname, handler, first_status = start_serial(portname)

      if not handler:
        print(f"Failed to start configured knob interface {str(i)}. Skipping.")
        continue

      KNOB_INTERFACES[portname] = handler

      # TODO: Get unique ID from knob
      knob_id = portname

      if handler:
        KNOB_CONNECTION[knob_id] = {
            "handler": handler,
            "prev_position": first_status.current_position,
            "position_nonce": first_status.config.position_nonce,
            "press_nonce": first_status.press_nonce,
            "current_view": default_view
          }

        for message_type in [ "smartknob_state" ]:
          # Let each knob's private thread push data messages into the
          # central handling queue
          handler.add_handler(message_type, functools.partial(message_from_knob,
            command.Q_KNOB,
            knob_id,
            message_type)
          )

        # Give the knob a startup configuration
        apply_knob_view(knob_id, KNOB_CONNECTION[knob_id]["current_view"])

      else:
        print(f"Couldn't find a knob on {portname}...")

  if (verbose):
    print(f"Started communications with {len(KNOB_CONNECTION)} knob(s).")

  while True:

    cmd = command.Q_KNOB.get()

    if cmd is None:
      if (verbose): print("Terminating knob task.")
      break

    #if (verbose): print("Knob task got: " + str(cmd))
      

    if cmd["cmd"] == "view":
      # Someone has requested a configuration change for a knob
      new_knob_config = knob_views.get(cmd["view"], None)

      if not new_knob_config:
        print(f"Unable to find knob view {cmd['view']}. Check your app configuration.")
        continue

      # By default, apply to all knobs
      knob_ids = list(KNOB_CONNECTION.keys())

      # If one is specified, apply to that one
      if "knob" in cmd and cmd["knob"]:
        knob_ids = [ cmd["knob"] ]
        # TODO: Knob name translation

      for knob_id in knob_ids:
        apply_knob_view(knob_id, new_knob_config)


    elif cmd["cmd"] == "data":
      # Data has arrived from a knob
      #print(f"Message[{cmd['knob_id']}] ({cmd['message_type']}): {cmd['message']}")

      knob_id = cmd["knob_id"]
      msg = cmd["message"]

      if knob_id in KNOB_CONNECTION:
        handle_data(knob_id, msg)
        continue


  for name, state in KNOB_CONNECTION.items():
    try:
      state["handler"].shutdown()
    except:
      pass
