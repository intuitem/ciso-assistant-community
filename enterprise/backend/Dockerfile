FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
   PYTHONDONTWRITEBYTECODE=1 \
   POETRY_NO_INTERACTION=1 \
   POETRY_VIRTUALENVS_IN_PROJECT=1 \
   POETRY_VIRTUALENVS_CREATE=1 \
   POETRY_CACHE_DIR=/tmp/poetry_cache \
   DJANGO_SETTINGS_MODULE=enterprise_core.settings \
   HOME=/tmp

WORKDIR /code

RUN apt-get update && apt-get install -y \
   libyaml-cpp-dev \
   libffi-dev \
   libglib2.0-0 \
   pango1.0-0 \
   libcairo2 \
   locales \
   tzdata \
   gettext \
   fontconfig \
   fonts-freefont-ttf \
   build-essential \
   python3-dev \
   python3-numpy \
   libjpeg-dev \
   zlib1g-dev \
   libmagic1 \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/* \
   && locale-gen en_US.UTF-8 \
   && locale-gen ar_SA.UTF-8 \
   && locale-gen fr_FR.UTF-8 \
   && locale-gen pt_PT.UTF-8 \
   && locale-gen es_ES.UTF-8 \
   && locale-gen de_DE.UTF-8 \
   && locale-gen nl_NL.UTF-8 \
   && locale-gen it_IT.UTF-8 \
   && locale-gen pl_PL.UTF-8 \
   && locale-gen ro_RO.UTF-8 \
   && locale-gen hi_IN.UTF-8 \
   && locale-gen ur_PK.UTF-8 \
   && locale-gen cs_CZ.UTF-8 \
   && locale-gen sv_SE.UTF-8 \
   && locale-gen id_ID.UTF-8 \
   && pip install --no-cache-dir --upgrade pip poetry==2.0.1

COPY backend/pyproject.toml backend/poetry.lock ./
RUN poetry install --no-root \
   && rm -rf $POETRY_CACHE_DIR

COPY backend /code/
COPY enterprise/backend/enterprise_core /code/enterprise_core
COPY backend/startup.sh /code/

RUN groupadd --gid 1001 app && useradd --uid 1001 --gid 1001 app && mkdir -p /code/db && chown 1001:1001 /code/db
USER app
VOLUME /code/db

EXPOSE 8000
ENTRYPOINT ["poetry", "run", "bash", "startup.sh"]
