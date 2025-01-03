import re

import json5
from schema import Schema, And, Or, Use, Regex, Optional

def is_valid_regex(pattern):
    try:
        re.compile(pattern)
        return True
    except:
        raise
    return False

CONFIG_SCHEMA = Schema(
  {
    "nobbler": {
      "verbose": bool
    },

    "knobs": {
        "interfaces": [
          { "kind": And(str, lambda v: v in [ "serial" ])}
        ]

    },

    "actions": [
        {
          "name": str,
          Optional("placeholder", default="{value}"): str,
          Optional("relative", default=False): bool,
          Optional("scaling"): And([int], lambda l: len(l)==2),
          Optional("round", default=True): bool,
          Optional("get_command"): str,

          "steps": [
            Or(
                {
                    "kind": "log",
                    "message": str
                },
                {
                    "kind": "command",
                    "command": str
                },
                {
                    "kind": "view",
                    Optional("knob"): str,
                    "view": str
                }
            )
          ]
        }
    ],

    "views": [
      {
        "name": str,
        Optional("knob_action"): str,
        Optional("press_action"): str,
        "config": {
            "position": Use(int),
            "min_position" : Use(int),
            "max_position" : Use(int),
            "position_width_radians" : Use(float),
            "detent_strength_unit" : Use(float),
            "snap_point" : Use(float),
            "text" : str,
            "detent_positions" : [ int ],
            "snap_point_bias" : Use(float),
            "led_hue": Use(int)
        }
      }
    ],

    "triggers": [
      Or(
        {
          "kind": "active-window",
          "mappings": [
            {
              "filters": [
                {
                  "property": And(str, lambda s: s in ["title", "appname"]),
                  "pattern": And(str, is_valid_regex)
                }
              ],
              "views": [
                 {
                    Optional("knob"): str,
                    "view": str
                 }
              ]
            }
          ]
        }
      )
    ]
  }
)

def default_config():
  return {
    "nobbler": {
        "verbose": True
    },

    "knobs": {
      "interfaces": [
        { "kind": "serial" }
      ]
    },

    "actions": [
      { "name": "debug", "scaling": [0,100],
        "steps": [
            { "kind": "log", "message": "You've got mail: {value}" }
        ]
      },

      { "name": "system_volume", "scaling": [0,100], "round": True,
        "get_command": "python {scripts}/winvolume.py get",
        "steps": [
            { "kind": "command", "command": "python {scripts}/winvolume.py set {value}" }
        ]
      },

      { "name": "switch_bright",
        "steps": [
            { "kind": "view", "view": "brightness" } 
        ]
      },

      { "name": "switch_vol",
        "steps": [
            { "kind": "view", "view": "volume" } 
        ]
      }
    ],

    "views": [
        {
          "name": "volume",
          "knob_action": "system_volume",
          "press_action": "switch_bright",

          "config": {
            "position": 50,
            "min_position": 0,
            "max_position": 11,
            "position_width_radians": 0.27,
            "detent_strength_unit": 0.3,
            "snap_point": 1.1,
            "text": "Volume",
            "detent_positions": [],
            "snap_point_bias": 0,
            "led_hue": 8
          }
        },

        {
          "name": "bonzo",
          "knob_action": "debug",

          "config": {
            "position": 25,
            "min_position": 0,
            "max_position": 50,
            "position_width_radians": 0.094,
            "detent_strength_unit": 0.5,
            "snap_point": 1.1,
            "text": "Bonzo!",
            "detent_positions": [],
            "snap_point_bias": 0,
            "led_hue": 95
          }
        },

        {
          "name": "brightness",
          "knob_action": "debug",
          "press_action": "switch_vol",
          "config": {
            "position": 50,
            "min_position": 0,
            "max_position": 100,
            "position_width_radians": 0.047,
            "detent_strength_unit": 1,
            "snap_point": 1.1,
            "text": "Brightness",
            "detent_positions": [],
            "snap_point_bias": 0,
            "led_hue": 180
          }

        }

    ],

    "triggers": [
      {
        "kind": "active-window",

        "mappings": [
          # Match a window by title
          {
            "filters": [
              { "property": "title", "pattern": ".*[Nn]otepad.*" },
            ],
            "views": [
              { "view": "bonzo" },
            ] 

          },

          # A default, if no other window matches
          {
            "filters": [],
            "views": [
              { "view": "volume" }
            ]
          }
        ]
      }

    ]

  }

def validate_config(app_config):
  return CONFIG_SCHEMA.validate(app_config)