# Make starting a quick-form request a domain permission: published forms are offers in a domain, portals show each viewer what they can use, personal spaces are removed

- Status: Proposed
- Date: 2026-10-23
- Deciders: @eric-intuitem
- Related: [is-published-field-removal](is-published-field-removal.md) (members and default roles; this decision amends its Layer 1), [global-user-creator-role](global-user-creator-role.md), [notification-recipient-scoped-access](notification-recipient-scoped-access.md)

## Context

Quick forms (v4.0.2, behind the `quick_forms` flag) let people file a structured request — a derogation, a vendor review, a DPIA screening — into a domain, where reviewers decide on it. Requests start in four ways: from a portal tile pointing at a published form, from an inline portal tile carrying its own domain, reviewers and drafts policy, from an object page ("Assess tier", "Screen DPIA"), and by cloning a request.

Two of those paths authorize outside the IAM model. A published form's `audience_groups` says who may start a request (direct members, or every user when empty), and may land requests in any `submission_folder`, never checked against the publisher's rights. A request's `respondents` (users or teams, editable by the domain's writers) then grant reading, filling, submitting, dropping and cloning, and `clone` re-checks nothing. Inline tiles and object pages, by contrast, already require `add_quickformresponse` on the domain the request lands in. A portal's own audience, a list of user groups, only decides who sees it: every tile that starts something performs its own check, so viewers are shown tiles that refuse them, and every tile's settings — domains, forms, reviewers — reach every viewer.

Personal spaces ("My space", behind a general setting) give each user a domain of their own, created on first use, so that anyone can file a request, launch an assessment or create an object somewhere. The space comes with a direct Analyst assignment, granted as a side effect of a click, held outside any group, and making its owner a contributor (EE seats) as soon as the space is opened.

## Decision

We will make starting a request an ordinary domain permission, `add_quickformresponse`, granted to self-service populations by a new builtin role **Requester** (`BI-RL-REQ`, "Demandeur") holding only that permission. A published form is a quick form offered in a domain: its requests land in that domain, and it carries how they are handled. Portals grant nothing and show each viewer the tiles they can use. Each request has one requester. Personal spaces, which existed so that anyone could file or work somewhere, are removed.

**Concepts.** A **quick form** is catalog content. A **published form** offers a quick form in domain D, with how its requests are handled: reviewers, drafts policy, naming, projected result, forced review. A **request** lives in a domain and has exactly one requester, the user who started it, set once. A **portal** is a page of tiles: start tiles launch an action (a request, an assessment, an object), navigation tiles open a page, content tiles show what their author entered or captured for publication (a link, a metric, a document, a framework snapshot).

**Rules.**

1. **A domain decides what it accepts.** Requests are created only by rules 2, 3 and 4; there is no other creation path.
2. **From a published form.** Starting requires `add_quickformresponse` on the published form's domain, the published form to be enabled, and the user not to be a third party. The request lands in that domain, with the published form's handling.
3. **From an object.** Assessing an object with a quick form made for that kind of object requires `add_quickformresponse` on the object's domain and the object to be visible to the user. The request lands in the object's domain with the subject locked.
4. **Clone is a new start.** Rule 2 or rule 3 is checked again for the clone.
5. **Own requests.** The requester reads their request, edits, attaches, submits and deletes it while it is a draft, and drops it before the decision — as long as they hold `add_quickformresponse` on its domain. This is the only per-person rule: it narrows a domain permission and never grants on its own.
6. **Processing.** `view_quickformresponse` on D shows every request in D. `approve_quickformresponse` on D allows claiming, releasing, sending back, accepting and rejecting. A requester never decides their own request unless self-validation is allowed.
7. **Publishing.** Managing D's published forms requires `add_quickformpublication` or `change_quickformpublication` on D. Since requests land only in the published form's domain, a publisher opens intake into their own domain and nowhere else.
8. **Effects.** Accepting writes each effect under the decider's own permission on its subject. Automatic application at submission happens only when the submitter holds every permission the effects need, every scored question is answered, and neither the form nor the published form requires review.
9. **Disclosure.** A requester sees the form, their own requests with their decisions and outcomes, the projected result when the published form enables it (always for an object assessment), and, for object questions and the subject, only objects they can already view.
10. **Records.** Drafts may be deleted by their requester; a dropped request stays on record; the facts snapshot is frozen at submission; only administrators delete a closed request.
11. **Portals show each viewer what they can use.** A start tile is shown to the users who may perform its action in at least one domain it allows: start a request from a published form it offers (rule 2), create an assessment (`add_complianceassessment`), or create an object of its kind. A navigation tile is shown to the users who may view what it opens. A content tile needs no permission and is shown to every internal user. A portal is listed to whoever it shows at least one tile; it has no audience, the default portal is only the one that opens first, and the public setting only adds anonymous access through the portal's token. A tile points either at a published form, or at a quick form, in which case it offers the published forms of that quick form the viewer can start, asking for the domain when there are several.
12. **No personal spaces.** Nothing creates a domain on a user's behalf, and domain pickers offer only existing domains: requests, assessments and objects start in domains an administrator created.

**The Requester role.** It holds exactly `add_quickformresponse`, which joins the permissions that consume no seat: filing a request, free today through published forms, stays free. A domain's group `BI-UG-REQ` is created the first time a published form is placed in that domain, assigned recursively like the other generated groups. **A grant of the Requester role carries no default role:** its members do not become members of the domain (amending Layer 1 of [is-published-field-removal](is-published-field-removal.md)). Filing open to everyone who signs in with SSO is the domain's Requester group mapped from an IdP group holding every internal user. With auto-provisioning on, the IdP's groups are read again at every sign-in, including the one that creates the account, so membership follows the IdP. When the IdP sends no such group, listing the Requester group in the SSO default groups covers the accounts SSO creates, and an administrator adds the others.

## Consequences

- **Requests land where they are handled.** Different populations need different domains. One quick form serves several business units by being published in each unit's domain; the UI must let a publisher offer a quick form in several domains at once.
- **Requesters are not contributors.** `add_quickformresponse` is exempt from seat counting, so opening filing to all staff costs no license. Holders of other write permissions — analysts, domain managers, auditees — remain contributors through those.
- **Domain members file through their domain's published forms.** Every role already holding `add_quickformresponse` — analyst, domain manager, administrator, auditee — can start requests from the published forms of the domains where it holds it.
- **"Empty means everyone" disappears.** No grant means nobody may file.
- **Inline tiles disappear.** Their domain, reviewers, drafts policy and naming move into published forms; a tile pointing at a quick form replaces the inline tile whose clicker picked the domain.
- **Respondents no longer carry rights.** Asking named people to answer a request is out of scope and needs its own decision.
- **Personal spaces disappear.** Published forms and Requester groups serve filing; a private workspace is an ordinary domain an administrator creates for a person or a team. Opening "My space" no longer creates a domain and an assignment, nor turns a reader into a contributor. Create forms and assessment tiles stop offering "My space", so under rule 11 an assessment tile is shown only to users who may create an assessment in some domain.
- **Membership is counted as everywhere else**, inheritance through IdP groups included.
- **One more group per domain that has a published form**, not per domain. The IAM-groups cleanup removes it with the rest of the family when unused.
- **Portals follow IAM.** Nobody is shown a tile that would refuse them, and a tile's settings reach only the users who can use it. User groups grant rights and no longer double as display lists: a page for a narrower population is built from tiles that population can use, and restricted information belongs in objects reached through navigation tiles, not in content tiles, which every internal user sees.
- **API clients:** published forms lose `audience_groups` and `submission_folder` (read-only for one release). On requests, `respondents` is replaced by a read-only `requester`, and creating a request through the generic endpoint is refused; `reviewers` stays. A portal tile can no longer carry inline quick-form settings, and portals lose `audience_groups` (read-only for one release). The start endpoints, `portals/mine/`, `quick-form-publications/mine/` and `my-requests/` keep their shape; `portals/mine/` lists only the portals that show the caller a tile, and a portal's content returns only the tiles the caller can see. General settings lose `personal_folders` and `personal_folders_parent`, the `PE` folder type disappears, and creation and launch endpoints refuse the `__personal__` domain.
- **Migration never widens access.**
  - Each request's requester is its user respondent, else its submitter.
  - A published form whose submission domain differs from its own domain moves to that domain, and its audience groups receive the Requester role there.
  - An empty audience becomes the domain's Requester group holding the active internal users at migration time, reported so that administrators can feed it from an IdP group or the SSO defaults, or narrow it.
  - An inline tile becomes a published form in its fixed domain; one whose clicker picked the domain becomes published forms in the domains where its requests landed, behind a tile pointing at the quick form. That narrows it: it no longer offers the other domains where its viewers could file, and a tile whose requests never landed offers nothing until the quick form is published. Such tiles are reported.
  - Portal audiences are dropped. A portal whose audience limited who saw its content tiles returns to draft and is reported, so that its author decides before that content reaches every internal user.
  - Each personal domain becomes an ordinary domain under the same parent. Its owner's direct Analyst assignment moves to a custom group holding only them: a custom group, unlike a domain's standard groups, grants no default role, so nothing widens. Each is reported, those whose owner is gone included, so that administrators can merge them into team domains.
  - Anything else, such as a request with no requester, is reported, not approximated.
- **Required:** the Requester role holds exactly `add_quickformresponse`. Adding `view_quickformresponse` would show every request in the domain to every requester.
- **Required:** a Requester grant never carries a default role.
- **Required:** every path that creates a request — published forms, object pages, clone, API — checks rule 2 or rule 3. A new path that creates requests needs a test proving it.
- **Required:** object-question options and subject validation use the requester's own visibility only.
- **Required:** the requester is set at creation and is not writable afterwards.
- **Required:** a tile is shown with the same check as the action it launches, which runs again on click. A tile kind counts as content only if it needs no permission and shows nothing but what its author entered or captured for publication.

## Security

**Conclusion: the change lowers risk.** One existing permission, checked on the domain where the request lands, replaces two access lists that bypassed the IAM model — one of them failing open when empty — and the unchecked landing domain. The clone bypass, cross-domain landing and object-list disclosure are closed, and the remaining capability is granted, audited and revoked like every other right. Portals stop following a third list: what a viewer is shown follows what their rights let them do. And no right is granted as a side effect any more: opening "My space" created a domain and gave its user a direct Analyst assignment on the fly.

### Why a requester cannot turn filing into more access

1. **The permission creates requests and nothing else.** The Requester role carries no view on the domain's objects and no default role. A requester sees only their own requests, through rule 5.
2. **They cannot choose where a request lands or who reviews it.** It lands in the published form's domain or the assessed object's domain, with the published form's handling.
3. **They cannot learn about objects they cannot see.** Object questions and subjects offer only what their own permissions show.
4. **Filing does not change data.** Accepting writes under the decider's permissions, and automatic application only under the submitter's own permissions, so a review never grants what the submitter lacked.
5. **They cannot decide their own request.** Deciding needs `approve_quickformresponse` on the domain, and is refused on one's own request unless self-validation is allowed.
6. **A publisher cannot open a channel into a domain they do not govern.** Requests land only in the published form's own domain, which the publisher manages.
7. **Revocation is complete and fails closed.** Removing a member, a group or a role assignment ends filing and access to past requests; deleting a group narrows access, never widens it.
8. **Third parties stay out.** They never sign in with SSO, so no IdP group reaches them, and Layer 1 places them only in enclave groups: they cannot be in a domain's Requester group, and rule 2 refuses them as a backstop.

### Why a portal cannot widen access

1. **A portal grants nothing.** Each tile is shown with the check of the action it launches, and the action checks again when the tile is clicked.
2. **Viewers learn only about what they can use.** A tile the viewer cannot use is not sent, nor are its domain, forms or reviewers.
3. **Content tiles read nothing live from the instance.** They show only what their author entered or captured for publication: text, links, public documents, framework snapshots.

### Remaining risks, accepted as low

- **Requests are a write channel into the domain.** A population member can create requests and attach files there. This is bounded by the population and the one-draft default; only file questions accept attachments, executables are refused by extension and content, and sizes are capped; every request names its requester.
- **Unfinished drafts are readable by the domain team.** Holders of `view_quickformresponse` see drafts in progress. They are the people who process requests.
- **The projected result reveals what accepting would write,** for example a vendor's tier. It is off by default for published forms and enabled per published form.
- **Everyone holding `add_quickformresponse` on a domain can use all of its published forms.** That is the intent: a domain's members use its intake, and a published form meant for a narrower population belongs in its own domain.
- **Nothing but its membership limits a Requester group.** Filing costs no seat, so the license is no brake on opening it widely; who may file is entirely an administrator's choice, visible in the group's member list.
- **What an author types into a content tile reaches every internal user.** The exposure is limited to what the author chose to write, as on any page they publish.
- **Membership through an IdP group is refreshed at sign-in.** Someone the IdP removes from the group keeps filing until their session ends, as with every right that comes from the IdP.

### What would change this assessment

This conclusion holds while the Requester role keeps exactly `add_quickformresponse`, its grants carry no default role, requests land only in the published form's or the assessed object's domain, no list on a request grants rights, and every tile is shown with the check of its action. Adding a permission to the role, letting requests land elsewhere, reintroducing respondent or audience lists — including to ask named people to answer — letting a tile show live data from the instance, or granting rights as a side effect of a user's action requires a new decision.
