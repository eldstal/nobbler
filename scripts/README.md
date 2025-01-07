## Nobbler scripts

This directory contains useful scripts for system interaction. This functionality doesn't really belong in Nobbler, but is probably useful for common tasks you might want your knob to perform.

The `scripts/` directory is automatically substituted for `{scripts}` before invoking action commands,
so you can configure Nobbler to call these as `python {scripts}/winvolume.py`.

Some have extra external dependencies, and these can be installed using

```
pip install -r requirements.txt
```

If you've got a venv or pipx environment for Nobbler, install them in that environment.

### winvolume.py

Reads and controls Windows system volume via `pycaw`. The `watch` mode outputs a percentage only when volume changes, so it's useful for passive monitoring.

```
winvolume.py get
winvolume.py watch
winvolume.py set <percentage>
winvolume.py change +percent
winvolume.py change -percent
```

