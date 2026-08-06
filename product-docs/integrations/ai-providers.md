---
description: >-
  How to connect the in-product chat assistant to a hosted AI provider such as
  OVHcloud AI Endpoints or OpenRouter, instead of running a model locally.
---

# Hosted AI providers

Compatible with: SaaS or on-premises, CE or Pro

The chat assistant talks to a model server rather than embedding a model of its own. That server can be local (Ollama, LM Studio, vLLM) or a hosted service. This page covers the hosted route — you sign up with a provider, paste a URL, a model name and an API key, and the assistant starts working.

The service needs to speak more of the OpenAI API than chat completions alone. It must answer `GET <base URL>/models`, since that is how the platform reaches the server at all, and the model you pick has to support tool calling and streamed responses — the assistant chooses a query with the first and streams the answer with the second. Temperature is only sent when **Send temperature to the model** is on, so a model that rejects a custom temperature can still be used with that switch off.

**OVHcloud AI Endpoints** and **OpenRouter** are documented here because they cover the two common cases: European data residency with a single provider, and a broad model catalogue behind one account.

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

Save the form. Saving stores the settings and drops the cached connection so the next question picks them up — it does not contact the provider, so a wrong key or model name surfaces on the first question rather than here. Use the `curl` commands below to check the values before you paste them.

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

`gpt-oss-120b` and `Mistral-Small-3.2-24B-Instruct-2506` are the two we have exercised against the assistant: both drive its tool calling and answer in the language the question was asked in. Other models in the catalogue may work equally well — a model that answers a plain chat completion can still fall short on tool calling, so try a question that reads your data before settling on one.

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

Each question the assistant answers costs two requests to the provider: one to choose a query, one to write the answer. OVHcloud rate-limits authenticated requests, and the allowance depends on your Public Cloud project and the model — check [their AI Endpoints documentation](https://docs.ovhcloud.com/fr/guides/public-cloud/ai-machine-learning/ai-endpoints-getting-started) for the figures that apply to you. Worth doing before rolling the assistant out to many simultaneous users.

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
export OPENROUTER_API_KEY="sk-or-v1-your-key-here"

curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
  -d '{
    "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "messages": [{"role": "user", "content": "What is the meaning of life?"}]
  }'
```

A reply containing `choices[0].message.content` confirms the key and the model identifier for a plain completion. It does not exercise tool calling or streaming, so a model that passes here can still fail once the assistant asks it to choose a query — see [Checking it works](#checking-it-works).

## What stays on your own infrastructure

Choosing a hosted provider sends **chat prompts** there — the question, the conversation history, and the retrieved context that answers it. That context contains your data, so treat the choice of provider as a data-processing decision.

{% hint style="warning" %}
**OpenRouter is a gateway, not the endpoint.** It forwards each prompt to whichever vendor serves the model you named, or picks one for you when the model is a routed alias. Retention and training policies belong to that downstream vendor and differ between them, and controls such as zero-data-retention routing are account settings you opt into. Review them before pointing the assistant at your risk data — with OVHcloud the prompt stays with one named operator, which is why regulated organisations tend to prefer it.
{% endhint %}

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

The provider is contacted on the first question after the settings change or the service restarts, and a failure to reach it is logged there — not at the moment you save.
{% endstep %}
{% endstepper %}

## Cost

Both providers bill per token consumed, against the account as a whole — there is no per-user seat, and the platform does not meter or cap usage per user. Spending controls live with the provider: OpenRouter supports credit limits and per-key spending caps, and OVHcloud bills against the Public Cloud project. Set those limits there, since that is the level at which usage is actually metered.

Most of what a question costs is not the question. The assistant's fixed instructions, the conversation history, the retrieved records and the extra context added on an audit or risk assessment page dominate the input, so a short question on a busy page costs far more than a long one on an empty page. Expect a few thousand input tokens for a simple exchange and a multiple of that where the page carries a lot of context, against several hundred output tokens. Measure your own traffic before budgeting: model, context size and provider pricing all move the figure. Published rates change often, so check [OVHcloud's pricing](https://www.ovhcloud.com/fr/public-cloud/ai-endpoints/) or [OpenRouter's model list](https://openrouter.ai/models) for current figures.

## Related pages

- [General settings](../configuration/settings/general.md) — every field in the **Chat / AI assistant** section
- [Feature flags](../configuration/settings/feature-flags.md) — turning `chat_mode` on
- [Helm chart](../installation/helm-chart.md) — enabling chat and Qdrant on Kubernetes
