---
description: >-
  How to run Paul, intuitem's open EBIOS RM and GRC model, behind the chat
  assistant, on an on-premises instance or a SaaS one.
---

# Paul, the EBIOS RM model

Compatible with: SaaS or on-premises, CE or Pro

[Paul](https://huggingface.co/intuitem/Paul-Gen2-14B) is an open-weight model fine-tuned by intuitem from Mistral's Ministral 3 14B. It specialises in EBIOS Risk Manager, ISO/IEC 27005 and security homologation, answers in French and English, and is trained to call the assistant's tools. It is a research project, published under the base model's Apache 2.0 licence.

Paul is not built into the platform and there is no checkbox that turns it on. It is one model among others: you serve it from a model server, then point the chat assistant at that server, exactly as you would for any local model. This page covers both steps.

## Before you start

Paul is used by the chat assistant, so the assistant must be available first. If the **Chat / AI assistant** section is missing from **Extra** → **Settings**, one of these is the reason:

1. The backend and Huey worker are started with `ENABLE_CHAT=True`. On Helm, set `enabled: true` under the chat values; see [Helm chart](../installation/helm-chart.md#ai-assistant-chat-rag).
2. The `chat_mode` feature flag is on. See [Feature flags](../configuration/settings/feature-flags.md).
3. A Qdrant instance is reachable through `QDRANT_URL`. The Docker Compose files already ship one.

You also need a machine that can run the model: a GPU with 16 GB of memory or an Apple Silicon Mac with 16 GB or more runs the recommended `Q4_K_M` file (about 8 GB).

## On-premises, with Ollama

{% stepper %}
{% step %}
### Serve Paul

On the machine with the GPU, install [Ollama](https://ollama.com), then create a `paul` model from the published GGUF with a Modelfile:

```
FROM hf.co/intuitem/Paul-Gen2-14B-GGUF:Q4_K_M
PARAMETER num_ctx 16384
```

```bash
ollama create paul -f Modelfile
ollama run paul "Quels sont les cinq ateliers d'EBIOS RM ?"
```

The chat template and Paul's own system prompt come with the GGUF file. `num_ctx` raises Ollama's context window: the assistant sends its instructions, the conversation and the retrieved records in every request, which can overflow a small default window without any error.
{% endstep %}

{% step %}
### Let the platform reach it

The **Ollama URL** is checked when you save it and must resolve to a public address, to prevent server-side request forgery. A model on your own network needs `ALLOW_PRIVATE_NETWORK_REQUESTS=True` on the backend and Huey worker.

If Ollama runs on the Docker host itself, the containers reach it at `http://host.docker.internal:11434`. On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` to both services and start Ollama with `OLLAMA_HOST=0.0.0.0` so it listens beyond loopback. Check from the backend container:

```bash
docker compose exec backend curl -s http://host.docker.internal:11434/api/tags
```
{% endstep %}

{% step %}
### Point the assistant at Paul

Open **Extra** → **Settings** → **Chat / AI assistant** and set:

| Field | Value |
| --- | --- |
| **LLM provider** | `Ollama` |
| **Ollama URL** | `http://host.docker.internal:11434`, or the address of your GPU machine |
| **LLM model** | `paul` |
| **Temperature** | `0.2`, the value Paul is tuned for |

Leave **System prompt** empty to keep the platform's default instructions. Save.
{% endstep %}
{% endstepper %}

Any server that speaks the OpenAI API works too (LM Studio, llama.cpp's `llama-server --jinja`, vLLM): pick `OpenAI-compatible (hosted gateway or local server)` instead and follow [Hosted AI providers](ai-providers.md) for the fields.

## On SaaS

A SaaS instance runs on intuitem's infrastructure, so two things change:

- **The assistant is enabled for you.** `ENABLE_CHAT` is an environment variable you cannot set yourself on SaaS: open a ticket on the [customer support portal](https://intuitem.atlassian.net/servicedesk/customer/portal/4) to enable it, then turn on `chat_mode`.
- **The model must be reachable from the internet.** Private addresses are rejected, so the SaaS backend cannot reach a model on your laptop or office network.

Serve Paul on a machine you control with a public HTTPS address, behind an OpenAI-compatible server that checks an API key, for example `llama-server -m Paul-Gen2-14B-Q4_K_M.gguf --jinja --temp 0.2 -c 16384 --api-key <key>` or `vllm serve intuitem/Paul-Gen2-14B --api-key <key>`, behind a TLS reverse proxy. Then set **LLM provider** to `OpenAI-compatible (hosted gateway or local server)`, **API base URL** to your address ending in `/v1`, **Model name** to the model your server reports at `/v1/models`, and **API key** to your key.

{% hint style="warning" %}
**Do not expose a bare Ollama server.** Ollama has no authentication, so anyone who finds the address can use your GPU. Put a server that checks a key, or a reverse proxy that does, in front of it.
{% endhint %}

Prompts, conversation history and the retrieved records then travel from the SaaS instance to your server, and nowhere else.

## Checking it works

Open the chat assistant and ask a question that reads your data, such as *how many risk scenarios do we have?*, then an EBIOS RM question such as *quels sont les livrables de l'atelier 3 ?*. If the reply starts with **"No LLM configured — showing retrieved context"**, the platform could not reach the model server: check the URL, the model name and, on-premises, `ALLOW_PRIVATE_NETWORK_REQUESTS`. See [Checking it works](ai-providers.md#checking-it-works) for the full list.

## What Paul knows

Paul was trained on public reference documents, mostly ANSSI's: the EBIOS RM guide (v1.5) and its method sheets, the training material, the EBIOS RM label specification, the homologation guide (v2.2) and its method sheets, the hygiene guide and the ReCyF (NIS2). The full list of sources and their licences is on the [model card](https://huggingface.co/intuitem/Paul-Gen2-14B).

Its answers can be wrong, especially on the exact wording of rating scales and the values in the guide's worked examples: check them against the ANSSI guides before relying on them.

## Related pages

- [Hosted AI providers](ai-providers.md): the OpenAI-compatible fields in detail
- [General settings](../configuration/settings/general.md): every field in the **Chat / AI assistant** section
- [Feature flags](../configuration/settings/feature-flags.md): turning `chat_mode` on
- [Helm chart](../installation/helm-chart.md): enabling chat and Qdrant on Kubernetes
