---
description: >-
  User groups are built-in objects giving permissions to all users inside of
  them, with a specific role across a scope.
---

# User Groups

For now, it is not possible to create custom role assignments so you need to use built-in user groups. They are linking a domain with a role which contains precise permissions, that will be given to users in this group.

### Roles

Let's give some details on the 5 built-in roles:

| Role           | Permissions                                                                                                                       |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Administrator  | full access (except approval), and specifically management of domains, users and users rights                                     |
| Domain manager | full access to selected domains (except approval), in particular managing rights for these domains. Read access to global objects |
| Analyst        | read-write access to selected perimeters/domains. Read access to global and domain objects                                        |
| Auditor        | read access to selected perimeters/domains                                                                                        |
| Approver       | like reader, but with additional capability to approve risk acceptances                                                           |

{% hint style="info" %}
Django superuser is given administrator rights automatically on startup.
{% endhint %}

### Global user groups

Once your instance is created, three user groups are already present:

* Global - Administrator
* Global - Approver
* Global - Auditor

They give corresponding permissions on Global scope so on every object of your instance.

### Domain user groups

They are created for each domain you add. For example, if you create a domain _R\&D_, there will be:

* R\&D - Domain Manager
* R\&D - Analyst
* R\&D - Approver
* R\&D - Auditor

They give corresponding permissions on the domain scope so on every object inside _R\&D_.
