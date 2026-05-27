# Native Windows Development Scripts

This folder contains helper scripts for running the CISO Assistant backend in
native Windows development.

## Files

- `backend.ps1`: PowerShell launcher for the backend.
- `.win_native_dev_runserver.py`: Django `runserver` wrapper that increases the
  development server listen backlog.
- `convert_library_v2.bat`: Run `convert_library_v2.py` located in `backend` easily.

## Where to place them?

### > For `backend.ps1` & `.win_native_dev_runserver.py`

Copy the scripts from this folder at these paths from the CISO Assistant
repository root:

```sh
backend.ps1
backend/.win_native_dev_runserver.py
```

Then start the backend from the repository root:

```powershell
.\backend.ps1
```

### > For `convert_library_v2.bat`

Copy the script from this folder at this path from the CISO Assistant
repository root:

```sh
tools/convert_library_v2.bat
```

Then start the script when you need it, just as you would with `convert_library_v2.py` (without `python` at the beginning). For example:

```powershell
.\convert_library_v2.bat .\example_framework.xlsx
```

## Why they exist?

### > For `backend.ps1` & `.win_native_dev_runserver.py`

On native Windows, Django's development server can drain bursts of incoming API
connections more slowly than on Linux. During SvelteKit SSR, the frontend can
open many API connections at once; with Django's small default backlog, Windows
may intermittently return `ECONNREFUSED` before requests reach Django.

The Python wrapper keeps normal `runserver` behavior but raises the backlog with
`DJANGO_RUNSERVER_BACKLOG` (`512` by default).


### > For `convert_library_v2.bat`

We can't use the `tools/convert_library_v2.py` symlink, as symlinks don't work on Windows.

## About Python Virtual Environment (.venv)

In `backend.ps1`, set `$PythonRelativeExecutablePath` to the Python executable
that should run Django. A local `.venv` is recommended because it keeps
dependencies isolated and gives a predictable path, for example:

```powershell
$PythonRelativeExecutablePath = ".venv\Scripts\python.exe"
```
