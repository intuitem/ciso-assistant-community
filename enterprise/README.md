> [!WARNING]
> Both installation assume you're located in the root folder (`ciso-assistant-community/`)

## Testing locally 🚀

New: use the config builder on the `config` folder.

To run CISO Assistant Enterprise locally in a straightforward way, you can use Docker compose.

1. Launch docker-compose script with enterprise docker-compose.yml file:

```sh
./docker-compose-build.sh -f enterprise/docker-compose-build.yml     # Linux/MacOS
./docker-compose-build.ps1 -f enterprise/docker-compose-build.yml    # Windows
```

When asked for, enter your email and password for your superuser.

You can then reach CISO Assistant using your web browser at [https://localhost:8443/](https://localhost:8443/)

## Setting up CISO Assistant Enterprise for development

> [!NOTE]
> This section assumes that you have already set up the community frontend and backend, and use uv for managing the backend dependencies.

### Running the backend

1. Go to enterprise backend directory.

```sh
cd enterprise/backend
```

2. Install dependencies.

```sh
uv sync
```

3. Set the `SQLITE_FILE` environment variable if you use SQLite.

```sh
export SQLITE_FILE=db/ciso-assistant-enterprise.sqlite3
```

4. Apply migrations.

```sh
uv run ./manage.sh migrate
```

5. Create a Django superuser, that will be CISO Assistant administrator.

```sh
uv run ./manage.sh createsuperuser
```

6. Run the development server.

```sh
uv run ./manage.sh runserver
```

### Running the frontend

1. cd into the enteprise frontend directory.

```bash
cd enterprise/frontend
```

3. Start a development server (make sure that the django app is running).

```bash
make dev
```

If you want to start the frontend after launching it for the first time, **ALWAYS** run the following commands to avoid any bugs.

```sh
make clean
make dev
```

4. Reach the frontend on <http://localhost:5173>

<details>
<summary>[EXPERIMENTAL] Setting up CISO Assistant Enterprise for development on Windows without WSL2</summary>

## [EXPERIMENTAL] Setting up CISO Assistant Enterprise for development on Windows without WSL2

> [!CAUTION]
>
> ### Important note
>
> The best working solution for users developing on **Windows** is to use [Ubuntu](https://apps.microsoft.com/detail/9pdxgncfsczv) installed on [WSL2](https://apps.microsoft.com/detail/9p9tqf7mrm4r) (Docker is not required).
>
> Please note that the native running on Windows is still in **EXPERIMENTAL PHASE** and should **NOT** be used if you are unsure of what you are doing, or if you want to ensure stability throughout development.
> Nevertheless, we would love to hear any suggestions in order to enhance the development experience for Windows users. Please feel free to open an Issue/PR about it!

> [!NOTE]
> This section assumes that you have already set up the community frontend and backend, and use uv for managing the backend dependencies.
> 
> If you have already used the Community Edition, we strongly recommend that you clone the repository to a dedicated folder to avoid any conflicts with backend dependencies.

### Running the backend

0. Create a `.venv` in the root folder and activate it

```sh
python -m venv .venv
.\.venv\Scripts\activate 
```

1. Go to enterprise backend directory.

```sh
cd enterprise/backend
```

2. Install dependencies.

```sh
uv sync --active
```

3. Go back to root folder and apply migrations.

```sh
cd ..\..

# With SQLite
.\backend.ps1 --enterprise --migrate         # .\backend.ps1 -z -m

# With PostgreSQL
.\backend.ps1 --enterprise --pg --migrate    # .\backend.ps1 -z -p -m
```

4. Create a Django superuser, that will be CISO Assistant administrator.

```sh
# With SQLite
.\backend.ps1 --enterprise --createsuperuser         # .\backend.ps1 -z -c

# With PostgreSQL
.\backend.ps1 --enterprise --pg --createsuperuser    # .\backend.ps1 -z -p -c
```

5. Run the development server.

```sh
# With SQLite
.\backend.ps1 --enterprise --runserver         # .\backend.ps1 -z -r

# With PostgreSQL
.\backend.ps1 --enterprise --pg --runserver    # .\backend.ps1 -z -p -r
```


If you want to start the backend after setting it up, use the following command:
```sh
# With SQLite
.\backend.ps1 --enterprise          # .\backend.ps1 -z

# With PostgreSQL
.\backend.ps1  --enterprise --pg    # .\backend.ps1 -z -p
```

### Running the frontend

#### Prerequisites

You must follow the instructions in Section `[EXPERIMENTAL] Additional requirements for development on Windows without WSL2` beforehand in the [main documentation of CISO](../README.md#requirements) first.

Then, install the following dependencies via `pacman` using `MSYS2 UCRT64`.

```sh
pacman -S make rsync mingw-w64-ucrt-x86_64-fswatch
```

You will also need to add another path of some `MSYS2 UCRT64` binaries to your [system PATH environment variable](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables?view=powershell-7.6#set-environment-variables-in-the-system-control-panel) (usually, the binaries are in `C:\msys64\usr\bin\`) after installing the dependencies. You'll have to place it right under the first  `MSYS2 UCRT64` path you added.


The Makefile we're going to use needs some apps that we have installed on Windows. To allow MSYS2 to detect these Windows applications (e.g. pnpm, git, etc.), add the following user environment variables:

```conf
MSYS2_PATH_TYPE=inherit
```

#### Steps

1. Open a MSYS2 console in `enterprise/frontend` (it doesn't work with a PowerShell console without some extra steps).

2. Start a development server (make sure that the django app is running).

```bash
make dev
```

3. Reach the frontend on <http://localhost:5173>


If you want to start the frontend after launching it for the first time, **ALWAYS** run the following commands to avoid any bugs.

```sh
make clean
make dev
```


</details>