---
description: Main concepts of the mapping feature
icon: diagram-sankey
---

# Understand mapping

One common challenge when dealing with audits is about being able to reuse your assessment on one framework to move to a different one. This commonly refered to as mapping or crosswalk between standards.

This capability is supported on CISO Assistant and allows the user to create a projection of the content of an audit, given that a mapping is available.\
\
Mapping are library objects that can be customized, imported and submitted to the community. To see the available ones, head to the libraries store and filter to mapping:\
\
![](<../.gitbook/assets/image (1) (1).png>)



Mappings are essentially a representation of the links between assessable nodes of a framework, and for which we are using the convention documented on NIST's OLIR project.

Mapping is a directed graph linked a SRC framework to a TGT framework on which the nodes can have one of the following relationships:\
\
![](<../.gitbook/assets/image (2) (1).png>) &#x20;



To create yours, you can follow one of the examples on `/tools` or bootstrap a starter using the `prepare_mapping`script.



To apply a mapping, you needt to first load a mapping from the library. Then, head to your audit and click on `apply mapping`and select the targeted framework and see the projected being created ✨.&#x20;



Note: the apply mapping feature can also be reused to clone the audit and create a new revision, if the same framework and same scope are selected.&#x20;



