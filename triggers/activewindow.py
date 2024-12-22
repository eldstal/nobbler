import threading
import time
import re

import pywinctl

import command

THREAD = None
THREAD_RUNNING = False
WINDOW_POLLING_DELAY = 0.2

#
# Start a thread which keeps track of the current active window
# and sends events when it changes
#
def start_thread(app_config):
    global THREAD
    THREAD = threading.Thread(target=thread_main, args=(app_config,))
    THREAD.start()

    return THREAD

def stop_thread():
    global THREAD
    global THREAD_RUNNING

    if THREAD_RUNNING:
        THREAD_RUNNING = False
        THREAD.join()
        THREAD = None


def thread_main(app_config):
    global THREAD_RUNNING
    THREAD_RUNNING = True

    verbose = app_config["nobbler"].get("verbose", False)

    last_window = None

    # This is a polling loop.
    # There is no portable way to get
    # this in an event driven manner, as far as I know.
    while THREAD_RUNNING:
        window = pywinctl.getActiveWindow()

        if window is None:
            if verbose: print(f"No window focused.")
            command.window_focused("", "")

        if window != last_window:

            # On windows, getAppName() fails for some reason. Too bad.
            appname = ""
            try:
                appname = window.getAppName()
            except:
                pass

            if verbose: print(f"Window focused: appname=\"{appname}\"    title=\"{window.title}\"")
            command.window_focused(window.title, appname)
            
        last_window = window
        time.sleep(WINDOW_POLLING_DELAY)        


def matches(filter, window_info):
    prop = filter.get("property", "title")
    value = window_info.get(prop, None)

    if value is None:
        print("Trying to filter a trigger unknown window property {prop}. Check your configuration.")
        return False
    
    pattern = filter.get("pattern", ".*")

    try:
        res = re.match(pattern, value)
    except:
        print(f"Invalid regular expression \"{pattern}\" in window filter. Check your configuration.")
        return False
    
    if res:
        return True
    return False