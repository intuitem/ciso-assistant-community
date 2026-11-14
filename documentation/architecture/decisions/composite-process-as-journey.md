# Run a composite process as a journey started from an accepted request

- Status: Proposed
- Date: 2026-11-14
- Deciders: @nas-tabchiche

## Context

Some processes chain several assessments of one subject: a form that scopes it, audits whose requirements depend on that scoping, a risk assessment, and whatever earlier results call for next. A project security review, a vendor onboarding and a system accreditation have this shape. Each part exists as a module. Nothing holds one run of the whole.

Three structures hold part of a run. A preset journey has a library-backed definition, scaffolds objects and tracks steps, but it needs library rights on the root folder, creates everything up front, and has its steps ticked by hand. A project groups objects under an owner and dates, with no definition and no steps. A workflow instance routes and waits, but it is a run log with a time limit and cannot create a risk assessment.

CEL contexts are local: an audit reads its own answers, a form its own. A requirement's importance is fixed in its library. A form question cannot point at a person.

A quick form published as a request already gives intake: an audience, a review, a subject, outcomes, writes on accept.

## Decision

We will make the journey the record of one run of a composite process, and the preset its definition. A process is a preset and its libraries. Nothing in the product names one.

**Start.** A preset may name an intake quick form. Accepting a response to it starts a journey in the response's folder.

**Subject.** A journey is about one subject: the answer to the intake's subject question, which may sit on the reviewer's page, or else the object the preset names among those it creates. Members read the fields its type exposes in CEL as `subject`.

**Results.** The results of a run are the outcomes, values and answers of its accepted forms, and the computed values of its assessments once done. Members read them in CEL as `run`. A form page may be reserved for the reviewer and answered during review.

**What is created.** A scaffolded object may carry a condition over `run` and `subject`, evaluated at the start and each time either changes. The object is created once the condition holds. An object may be repeated over a list answer, one per item. A preset may also create draft form responses, each about an object of the run.

**What reads the results.** Requirement visibility, implementation group selection, form page visibility and form outcomes may use `run` and `subject`. A requirement may carry an importance expression: mandatory, recommended or nice to have for this run, shown on the audit in place of the library's.

**Roles.** A preset declares the roles of a run. A role is filled from a form answer, from the subject's contacts, or by the reviewer at acceptance. Objects, form responses and steps name the roles they are assigned to. For this a form question may point at a person.

**Changing answers.** An accepted form is never edited. A clone, reviewed and accepted, replaces it in the run. Members recompute and objects newly due are created. Nothing is deleted.

**Steps.** A step completes from the state of its target: response accepted, assessment done, validation flow accepted. Without a target it keeps its hand tick. If its target was not created, it is not applicable.

**End.** A journey is open, completed or abandoned. It completes with its last applicable step. A reviewer may abandon it with a reason. Once not open, it creates nothing and its results are frozen.

Workflows stay automation and react to journey events. A preset may scaffold a project.

## Consequences

- The journey page shows a run: subject, state, steps, members, roles, results.
- Starting a run needs no library rights. The preset's libraries must already be loaded: a start never loads one or changes a feature flag.
- Presets without an intake are applied by hand as today.
- Conditions never read work in progress: a form counts once accepted, an assessment once done.
- A fact the subject holds is read from the subject, so a change made outside the run reaches the members. A preset that also reads it from the form can disagree with itself.
- A subject can be in several journeys. Each reads it as it is now.
- An assessment belongs to at most one journey and finds it without a scan.
- Outside a journey `run` and `subject` are absent. A requirement that reads them stays visible with its library importance.
- A requirement hidden by a recompute keeps its result.
- A role grants nothing by itself. Assigning a questionnaire to a third party still opens its enclave to them, as today.
- Schema: an intake form, a subject and roles on the preset, a subject, a state and filled roles on the journey, a member link, an importance expression on the requirement. One migration, no data step.
- Risk levels computed from audits follow an audit as it is filled. See [risk-levels-from-audit-coverage](risk-levels-from-audit-coverage.md).
- Not decided here: a requirement whose result comes from another assessment of the run (mapping inference is the candidate), repeating rows in forms, a file answer becoming evidence, due dates computed from results, a report across members, action plan milestones, a run started by an event, a schedule or another run, a later run starting from the previous one's answers.

## Security considerations

Objects are created with the accepting reviewer's rights in the journey's folder, a third party's questionnaire in its enclave as today. If the reviewer could not create one of them by hand, nothing is created and the acceptance says why, as writes on accept already do.

What applies to a reader tells them facts of the run and of the subject, never the values. Internal members share a folder, and so their readers. A questionnaire in an enclave must not read answers or subject fields its third party may not know. Nothing enforces this: the preset's author owns it.

A person question offers only those who can read the response's folder, never people outside the organisation. Conditions are library CEL run by the existing evaluator.

## Alternatives considered

- **The project and its collection as the record.** Managers know it, with owner, dates and a responsibility matrix. It has no definition and no steps.
- **The workflow instance as the record.** Conditions, waits and tasks exist. A run log with a time limit is not a record kept for months, and each process would be a graph to author.
- **The intake response as the record.** It has a reference, a review and links to what it produced. It closes on acceptance, long before the process ends.
- **A new process model.** A fourth structure holding part of a run.
- **Fewer results: the intake only, or forms only.** Less to re-evaluate. A later form often decides what comes next, and so does what an assessment found.
- **Every scoping result written onto the subject and read only there.** One source of truth. Most answers have no field to land in.
- **What a write on accept produced, kept as a run result.** No second source. A field changed outside the run would not reach the members.
- **Implementation groups computed by a workflow at audit creation.** Works today. One-shot, and a requirement cannot require two conditions at once.
- **Recommended requirements as an implementation group.** No new expression. A group is fixed on the requirement, while importance changes from run to run.
- **The project's responsibility matrix for roles.** It exists. It needs a project per run and is filled by hand afterwards.
