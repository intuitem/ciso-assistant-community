---
description: Through implementation groups
---

# Multi-level support



Multiple frameworks have their requirements organized into subgroups, mostly cumulative but not always. We introduced it in v1.3.x better support for such a concept using the concept of `implementation groups` from CIS, but with a generic implementation to cover both cases.

{% embed url="https://vimeo.com/944716754" %}
illustration of implementation groups
{% endembed %}

When creating a new audit with a framework that supports implementation groups (IG), you'll get a drop-down menu to select the ones you want to use. They can be combined to suit your needs. If no implementation group is selected, the audit will start with all the requirements, and you can still update it to add or remove other IG.

CyFun and CIS, and FedRamp have been updated to take advantage of this feature. Other relevant frameworks are currently being updated.
