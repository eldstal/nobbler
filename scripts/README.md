## Nobbler scripts

This directory contains useful scripts for system interaction. This functionality doesn't really belong in Nobbler, but is probably useful for common tasks you might want your knob to perform.

The `scripts/` directory is automatically added to the end of $PATH or %PATH% before invoking action commands,
so you can configure Nobbler to call these.

Some have extra external dependencies, and these can be installed using

```
pip install -r requirements.txt
```

If you've got a venv or pipx environment for Nobbler, install them in that environment.

### winvolume.py

Reads and controls Windows system volume via `pycaw`.

```
volume.py get
volume.py set <percentage>
volume.py change +percent
volume.py change -percent
```

