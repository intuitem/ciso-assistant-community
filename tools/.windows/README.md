# Native Windows Development Scripts

This folder contains helper scripts for running the CISO Assistant backend in
native Windows development.

## Files

- `backend.ps1`: PowerShell launcher for the backend.
- `.win_native_dev_runserver.py`: Django `runserver` wrapper that increases the
  development server listen backlog.

## Where to place them?

Copy the scripts from this folder at these paths from the CISO Assistant
repository root:

```text
backend.ps1
backend/.win_native_dev_runserver.py
```

Then start the backend from the repository root:

```powershell
.\backend.ps1
```

## Why they exist?

On native Windows, Django's development server can drain bursts of incoming API
connections more slowly than on Linux. During SvelteKit SSR, the frontend can
open many API connections at once; with Django's small default backlog, Windows
may intermittently return `ECONNREFUSED` before requests reach Django.

The Python wrapper keeps normal `runserver` behavior but raises the backlog with
`DJANGO_RUNSERVER_BACKLOG` (`512` by default).

## About Python Virtual Environment (.venv)

In `backend.ps1`, set `$PythonRelativeExecutablePath` to the Python executable
that should run Django. A local `.venv` is recommended because it keeps
dependencies isolated and gives a predictable path, for example:

```powershell
$PythonRelativeExecutablePath = ".venv\Scripts\python.exe"
```
