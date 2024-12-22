
import command
import triggers.activewindow

def main(app_config):


  #trigger_kinds = set( [ t["kind"] for t in app_config["triggers"] ] )

  window_triggers = list(filter(lambda t: t["kind"] == "active-window",   app_config["triggers"]))


  # Only start this thread if the user has configured any window-related
  # triggers. Otherwise it will do a bunch of polling for no reason.
  if len(window_triggers) > 0:
    triggers.activewindow.start_thread(app_config)


  while True:

    cmd = command.Q_TRIGGER.get()

    if cmd is None:
      break

    if cmd["cmd"] == "window-focused":

      window_info = cmd
      for t in window_triggers:

        for m in t.get("mappings", []):
          #
          # The first mapping that matches our focused window gets applied.
          # If a mapping has no filters, it's a default and will match for sure.

          filters = m.get("filters", [])

          matches = True

          for f in filters:
            if not triggers.activewindow.matches(f, window_info):
              matches = False
              break

          if matches:
            # This mapping matches the window.
            # Apply all the views it asks for.

            for v in m.get("views", []):
              if "view" not in v: continue
              command.set_view(v["view"], v.get("knob", None))

            break

  print("Terminating trigger task.")
  triggers.activewindow.stop_thread()
