<!-- Copy this file to a short-kebab-slug.md named after the decision. Fill it in, delete what doesn't apply. -->

# Title stating the decision, not the topic

- Status: Proposed | Accepted | Replaced by [slug](slug.md)
- Deciders: who was in the room

## Context

What situation forced a decision. Constraints, forces, what we knew at the time. Two or three paragraphs max.

## Decision

What we chose, stated actively: "We will ...". One paragraph.

## Consequences

What becomes easier, what becomes harder, what is now forbidden or required. This is the section future readers act on, so make constraints explicit and imperative.

## Security considerations

Never leave this out. If the decision changes nothing for security, say so in one sentence and why. For a small change, a short list of risks and their mitigations is enough. For anything touching authentication, authorization, secrets, outbound requests, parsing of untrusted input or the supply chain, use the subsections below ([full-view-permissions](full-view-permissions.md) and [mcp-app-access-model](mcp-app-access-model.md) are worked examples).

**Conclusion: one sentence on whether the decision adds, removes or moves risk.**

### Threat model

What is worth protecting (data, credentials, rights), who we assume is attacking (unauthenticated caller, user of another domain, compromised component, malicious library) and which trust boundaries the decision creates or crosses.

### Why the attack fails

Numbered invariants, each one a property the code holds, not an intention. Prefer designs where a mistake hides data or refuses a request rather than exposing it.

### Verification

The tests that hold each invariant, by file. Say which checks are done by hand.

### Remaining risks, accepted as low

Each risk in bold, then why we accept it and what limits it.

### What would change this assessment

The changes that reopen the question and require a new decision.

## Alternatives considered

Each option we didn't pick, with a one-line reason. Written down so nobody has to redo this discussion next year.
