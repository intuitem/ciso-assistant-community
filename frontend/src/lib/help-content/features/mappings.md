---
description: Main concepts of the mapping feature
---

# Mappings

One common challenge when dealing with audits is reusing your assessment on one framework to move to a different one. This is commonly referred to as **mapping** or **crosswalk** between standards.

CISO Assistant supports this capability and lets you create a projection of the content of an audit, given that a mapping is available.

Mappings are library objects that can be customised, imported, and submitted to the community. To see the available ones, head to the libraries store and filter to mapping:

![Mappings library filter view](<../.gitbook/assets/image (1) (1) (1) (1) (1) (1).png>)

Mappings are essentially a representation of the links between assessable nodes of a framework, using the convention documented on NIST's OLIR project.

A mapping is a directed graph linking a SRC framework to a TGT framework, where the nodes can have one of the following relationships:

![Example mapping relationship types between framework nodes](<../.gitbook/assets/image (2) (1) (1) (1) (1).png>)

To create your own, follow one of the examples under `/tools` in the repository, or bootstrap a starter using the `prepare_mapping` script.

To apply a mapping, first load it from the library. Then head to your audit, click `apply mapping`, select the targeted framework, and watch the projection get created.

The list of targets isn't limited to frameworks you mapped directly. If a mapping exists from your framework to a pivot (e.g. ISO 27001) and from that pivot to another framework, the engine **chains them automatically** and offers the far framework as a target too — no dedicated crosswalk required. See [transitive inference](../concepts/mappings.md#transitive-inference-pivot-mappings) for how chained coverage is computed.

> The apply-mapping feature can also be reused to clone an audit and create a new revision, if the same framework and same scope are selected.
