# nobbler
Host-side control software for scottbez's [SmartKnob View](https://github.com/scottbez1/smartknob)


## Ideas
- Support for multiple named knobs
  - Needs firmware support for some sort of ID. MAC of esp32, probably

- Named actions
  - Run command
  - Send keypress

- Named configs
  - Control mode
  - Screen text
  - Action for value
  - Action for press
  - Run a command to get current value?
    - This will probably have to be a polling thing. Kind of sucks.

- Triggers to automatically switch config
  - Active window
  - "Button" press
    - Filter by current config
    - If knob A is on "volume", switch it to "brightness"
  - Named knob to affect (or first)
