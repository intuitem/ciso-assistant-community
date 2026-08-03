---
description: >-
  How to connect the in-product chat assistant to a hosted AI provider such as
  OVHcloud AI Endpoints or OpenRouter, instead of running a model locally.
---

# Hosted AI providers

Compatible with: SaaS or on-premises, CE or Pro

The chat assistant talks to a model server rather than embedding a model of its own. That server can be local (Ollama, LM Studio, vLLM) or a hosted service. This page covers the hosted route — you sign up with a provider, paste a URL, a model name and an API key, and the assistant starts working.

Any service that speaks the OpenAI chat completions API will work. **OVHcloud AI Endpoints** and **OpenRouter** are documented here because they cover the two common cases: European data residency with a single provider, and a broad model catalogue behind one account.

## Before you start

Three things must already be in place. If the **Chat / AI assistant** section described below is missing from your settings page, one of them is the reason.

1. **The instance must be started with `ENABLE_CHAT` set.** This is an environment variable on the backend and Huey worker, not something you can change from the interface. On Helm, set `enabled: true` under the chat values. Without it the chat feature flag is not exposed at all.
2. **The `chat_mode` feature flag must be on.** It is off by default. See [Feature flags](../configuration/settings/feature-flags.md).
3. **A reachable Qdrant instance**, which the assistant uses to retrieve your data and framework content. See [Helm chart](../installation/helm-chart.md).

You also need administrator rights — the settings page requires the permission to change global settings.

## Where the settings live

In the sidebar, open **Extra** → **Settings**, then expand the **Chat / AI assistant** section.

Set **LLM provider** to `OpenAI-compatible (LM Studio, vLLM, llama.cpp...)`. Despite the name listing local servers, this is the correct choice for any hosted OpenAI-compatible service, including both providers below. Three fields then appear:

| Field | What to enter |
| --- | --- |
| **API base URL** | The provider's endpoint, up to and including `/v1` — and no further |
| **Model name** | The exact model identifier from the provider's catalogue |
| **API key** | The key you generated with the provider |

{% hint style="warning" %}
**Stop the URL at `/v1`.** The platform appends `/chat/completions` itself, so the field takes `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` and not `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions`. The test commands later on this page show the longer form because `curl` needs the complete path — pasting that into the field produces a doubled path and every request fails.
{% endhint %}

{% hint style="warning" %}
**Model name is required here.** Its help text says you may leave it empty to use the server's default loaded model. That applies to local single-model servers. Hosted providers serve many models at once and will reject a request that does not name one.
{% endhint %}

Save the form. The platform checks the endpoint and key immediately, so a mistake surfaces at once rather than on the first question.

## OVHcloud AI Endpoints

A French provider, so prompts and data stay with a European operator — often the deciding factor for regulated organisations. Models are served from a single shared endpoint and billed per token, with no subscription.

Generate an API key from the OVHcloud console, following [their getting-started guide](https://docs.ovhcloud.com/fr/guides/public-cloud/ai-machine-learning/ai-endpoints-getting-started). Then enter:

| Field | Value |
| --- | --- |
| **API base URL** | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` |
| **Model name** | For example `gpt-oss-120b` |
| **API key** | Your OVHcloud token |

The full catalogue is readable without a key, which is the quickest way to confirm an exact identifier before pasting it:

```bash
curl -s https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/models | jq -r '.data[].id'
```

Good general-purpose choices are `gpt-oss-120b` and `Mistral-Small-3.2-24B-Instruct-2506`; both handle the assistant's tool calling reliably and answer in the language the question was asked in.

To confirm a key and model together before entering them in the interface:

```bash
curl https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OVH_AI_ENDPOINTS_ACCESS_TOKEN" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "What is the meaning of life?"}]
  }'
```

{% hint style="info" %}
Identifiers are case-sensitive and punctuation-sensitive. `Meta-Llama-3_3-70B-Instruct` uses underscores where the model's public name uses dots — copy identifiers from the catalogue rather than typing them.
{% endhint %}

OVHcloud applies a request-rate limit per project. Each question the assistant answers costs two requests: one to decide which tool to use, one to write the answer. Worth knowing if you plan to roll the assistant out to a large number of simultaneous users.

## OpenRouter

A gateway in front of many model vendors. One account and one key reach models from several providers, which makes it convenient for comparing options before committing.

Create a key from your [OpenRouter account](https://openrouter.ai/keys), then enter:

| Field | Value |
| --- | --- |
| **API base URL** | `https://openrouter.ai/api/v1` |
| **Model name** | For example `openai/gpt-oss-120b` |
| **API key** | Your OpenRouter key, beginning `sk-or-v1-` |

{% hint style="warning" %}
**OpenRouter model names are namespaced.** They always take the form `vendor/model` — `openai/gpt-oss-120b`, `mistralai/mistral-small-3.2-24b-instruct`. Entering a bare `gpt-oss-120b` fails. This is the single most common mistake when moving a working configuration from another provider.
{% endhint %}

The catalogue is public, so you can confirm an identifier the same way:

```bash
curl -s https://openrouter.ai/api/v1/models | jq -r '.data[].id'
```

Some models are offered at no cost with an identifier ending in `:free`, which is a practical way to try the assistant before deciding on a paid model. The free and paid variants of a model are separate entries and can differ in their limits, so check both.

To confirm a key and model together before entering them in the interface:

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-or-v1-your-key-here" \
  -d '{
    "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "messages": [{"role": "user", "content": "What is the meaning of life?"}]
  }'
```

A reply containing `choices[0].message.content` means the credentials and the model name are both good, and anything still failing afterwards is on the platform side rather than the provider's.

## What stays on your own infrastructure

Choosing a hosted provider sends **chat prompts** there — the question, the conversation history, and the retrieved context that answers it. That context contains your data, so treat the choice of provider as a data-processing decision.

Two things do **not** go to the provider:

- **Embeddings**, which power semantic search over your data and the framework knowledge base. The **Embedding backend** field offers only `Sentence Transformers (local)` and `Ollama`. Selecting a hosted LLM provider does not move embeddings to it — the default runs inside the platform and requires no external service.
- **Search and retrieval**, which happen against your own Qdrant instance before anything is sent onward.

{% hint style="info" %}
Hosted providers are reached over the public internet, so the platform's protection against requests to internal addresses does not apply to them and no extra configuration is needed. That protection only comes into play when pointing the assistant at a model on `localhost` or inside your own network.
{% endhint %}

## Checking it works

Open the chat assistant and ask something that requires reading your data, such as *how many applied controls do we have?*

A correct answer means the whole chain is working. If instead the reply begins with **"No LLM configured — showing retrieved context"** followed by raw excerpts, retrieval succeeded but the model server could not be reached. The platform deliberately falls back to showing what it found rather than failing outright.

Work through the likely causes in this order:

{% stepper %}
{% step %}
### Check the base URL ends at `/v1`

By far the most frequent cause, in both directions: a URL missing the `/v1` suffix, or one carrying `/chat/completions` on the end. The platform appends that part itself.
{% endstep %}

{% step %}
### Check the model name against the catalogue

Use the `curl` command for your provider above. Remember the `vendor/model` form on OpenRouter.
{% endstep %}

{% step %}
### Check the key is active and funded

Re-paste it if in doubt — the field is write-only and never displays what is stored, so a truncated paste is invisible. Confirm the account has credit and the key has not been revoked.
{% endstep %}

{% step %}
### Check the backend logs

A failed provider check is logged when the settings are saved, and again on the first question after a restart.
{% endstep %}
{% endstepper %}

## Cost

Both providers bill per token consumed, against the account as a whole — neither has a per-user seat or quota. If you need to attribute spend to individual users, set a spending alert with the provider; that is the level at which usage is actually metered.

Answering one question consumes roughly seven thousand input tokens and several hundred output tokens, most of it the assistant's fixed instructions and the retrieved context rather than the question itself. At the rates the models named above are typically offered, ordinary daily use by one person costs a small fraction of a euro per month. Published rates change often, so check [OVHcloud's pricing](https://www.ovhcloud.com/fr/public-cloud/ai-endpoints/) or [OpenRouter's model list](https://openrouter.ai/models) for current figures.

## Related pages

- [General settings](../configuration/settings/general.md) — every field in the **Chat / AI assistant** section
- [Feature flags](../configuration/settings/feature-flags.md) — turning `chat_mode` on
- [Helm chart](../installation/helm-chart.md) — enabling chat and Qdrant on Kubernetes
