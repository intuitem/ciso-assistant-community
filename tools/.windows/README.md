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


Then, follow the [instructions in the section dedicated to starting the backend.](#how-to-run-the-backend-on-windows)

### > For `convert_library_v2.bat`

Copy the script from this folder at this path from the CISO Assistant
repository root:

```sh
tools/convert_library_v2.bat
```

Then start the script when you need it, just as you would with `convert_library_v2.py` (without `python` at the beginning). For example:

```sh
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

## How to run the backend on Windows?

### Prerequisites

1. Check the [section explaining where to place the necessary scripts.](#-for-backendps1--win_native_dev_runserverpy)
2. Check the [section about .venv.](#about-python-virtual-environment-venv)
3. If you want to use PostgreSQL, [see this section.](#about-using-postgresql)
4. If you want to run the Enterprise Edition, check the very end of the dedicated documentation in [`enterprise/README.md`](../../enterprise/README.md#experimental-setting-up-ciso-assistant-enterprise-for-development-on-windows-without-wsl2).


### If you're starting the backend for the first time

1. Apply migrations.

```sh
# With SQLite
.\backend.ps1 --migrate         # .\backend.ps1 -m

# With PostgreSQL
.\backend.ps1 --pg --migrate    # .\backend.ps1 -p -m
```

2. Create a Django superuser, that will be CISO Assistant administrator

```sh
# With SQLite
.\backend.ps1 --createsuperuser         # .\backend.ps1 -c

# With PostgreSQL
.\backend.ps1 --pg --createsuperuser    # .\backend.ps1 -p -c
```

3. Run development server

```sh
# With SQLite
.\backend.ps1 --runserver         # .\backend.ps1 -r

# With PostgreSQL
.\backend.ps1 --pg --runserver    # .\backend.ps1 -p -r
```

### If you start the backend after setting it up

Start the backend from the repository root:

```sh
# With SQLite
.\backend.ps1

# With PostgreSQL
.\backend.ps1 --pg    # .\backend.ps1 -p
```


## About Python Virtual Environment (.venv)

In `backend.ps1`, set `$PythonRelativeExecutablePath` to the Python executable
that should run Django. A local `.venv` is recommended because it keeps
dependencies isolated and gives a predictable path, for example:

```powershell
$PythonRelativeExecutablePath = ".venv\Scripts\python.exe"
```

## About using PostgreSQL

On Windows, you can also use a PostgreSQL database instead of SQLite. To do so, follow these steps:

1. Use the [official installer](https://www.postgresql.org/download/) to get PosgreSQL and pgAdmin.
2. Open pgAdmin.
3. Click `Servers` in the right sidebar and enter your password.
4. Right click `Login/Group Roles` then click `Create > Login/Group Roles...`
   1. In `General`: Enter a `Name` (e.g. `ciso-assistantuser`).
   2. In `Privileges`: Enable everything <u>except</u> `Superuser?` & `Can initiate streaming replication and backups?`.
   3. In `Definition`: Enter a `Password`.
   4. Click `Save`.
5. Right click on `Databases` then `Create > Databases...`.
   1. In `General`:
      * Enter a `Name` (e.g. `ciso-assistant`).
      * Set the user you just created as the `Owner` (e.g. `ciso-assistantuser`).
   2. In `Security`:
      * Click `+`.
      * Select the user you just created as the `Grantee`.
      * Click the blank `Privileges` field and check `ALL`.
    3. Click `Save`.

Once the database has been created, locate the section in the [`backend.ps1`](./backend.ps1#207) script that contains the following code:

```powershell
if ($UsePostgres) {
   $PostgresEnvironment = @{
      POSTGRES_NAME = "ciso-assistant"
      POSTGRES_USER = "ciso-assistantuser"
      POSTGRES_PASSWORD = "<XXX>"
      DB_HOST = "localhost"
      DB_PORT = "5432"
   }
   #...
}
```

Replace the variable values with the ones you use for you PostgreSQL database.
_Note: `DB_HOST` and `DB_PORT` are already set to the PostgreSQL default values on Windows._

To start the backend with PostgreSQL, remember to use the `-p/--pg` parameter every time you run the PowerShell script. 