---
description: Tag objects across modules with free labels, see where each label is used, and clean up duplicates
---

# Labels

A **label** is a free tag you put on objects to sort and filter them: `pci-scope`, `q3-review`, `crown-jewel`. Labels cut across modules, so the same label can tag an applied control, an audit, an asset and a vendor assessment, and every list can filter on it.

## What can carry labels

Most operational objects take labels, among them:

- applied controls, risk scenarios, assets, evidences, findings and findings binders, incidents, vulnerabilities, threats, reference controls and task definitions;
- assessments: audits, risk assessments, EBIOS RM studies, quantitative risk studies, business impact analyses, entity assessments and threat models;
- third parties (entities, solutions, contracts, representatives), processings, projects, accreditations, collections, documents and validation flows.

Set them in the object's **Labels** field. Typing a label that doesn't exist yet creates it. On a list, labels can be shown as a column, used as a filter, and added or removed in bulk with **Labels** > **Add** or **Remove** in the batch actions (see [Working with tables](working-with-tables.md)).

## The labels list

**Extra > Labels** lists every label with its **Usage**: how many objects carry it. Filter the list on **Usage** to clean up:

- **Unused** — labels no object you can view carries. A label used only on objects outside your reach still shows here, so check with an administrator before deleting it.
- **Used once or twice** — often typos or one-offs.
- **Look-alikes** — labels that differ only by case, hyphens or underscores, such as `PCI-scope` and `pci_scope`.

Open a label to see the objects carrying it, one tab per kind of object. Only the kinds where the label is used are shown, and only the objects you are allowed to view are counted.

## Merge labels

To fold duplicates into one, select them in the labels list and choose **Merge labels** in the batch actions. Pick the **Label to keep**: every object tagged with the others gets it instead, then the others are deleted. The dialog sums up the change before you confirm with **Merge into …**.

Merging needs permission to change the label kept and to delete the others.

## Related

- [Working with tables](working-with-tables.md)
- [Search](search.md)
