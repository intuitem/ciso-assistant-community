FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  libyaml-cpp-dev \
  curl \
  ca-certificates && \
  rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/0.6.9/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

RUN apt-get clean

COPY . .

RUN uv sync --frozen

EXPOSE 8000
ENTRYPOINT ["uv", "run", "bash", "entrypoint.sh"]
