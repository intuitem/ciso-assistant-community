<script lang="ts">
	import { invalidateAll, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { tick } from 'svelte';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import CreateModal from '#lib/components/Modals/CreateModal.svelte';
	import AutocompleteSelect from '#lib/components/Forms/AutocompleteSelect.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { getModalStore } from '#lib/components/Modals/stores.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { hasPermissionAnywhere, isAccessAllowed } from '#lib/utils/access-control.js';
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';
	import type { PageData } from './$types';
	import {
		KINDS,
		PEOPLE,
		READINESS,
		SECTIONS,
		STAGES,
		interviewPlan,
		worstOf,
		requestList,
		requestListTsv,
		sectionOf,
		keyOf,
		sessionPlan,
		todos,
		unpairedOf,
		type ActorRef,
		type Preparation,
		type PrereadItem,
		type Session,
		type Readiness
	} from '../preread';

	let { data }: { data: PageData } = $props();

	const items: PrereadItem[] = $derived(data.preread.items ?? []);
	const SHOWN: Readiness[] = ['gap', 'weak', 'to_confirm', 'ready', 'excluded'];
	const STYLE: Record<Readiness, { bar: string; text: string; border: string; icon: string }> = {
		gap: {
			bar: 'bg-error-500',
			text: 'text-error-600-400',
			border: 'border-error-500',
			icon: 'fa-solid fa-circle-exclamation'
		},
		weak: {
			bar: 'bg-warning-500',
			text: 'text-warning-700-300',
			border: 'border-warning-500',
			icon: 'fa-solid fa-triangle-exclamation'
		},
		to_confirm: {
			bar: 'bg-primary-400',
			text: 'text-primary-700-300',
			border: 'border-primary-400',
			icon: 'fa-solid fa-circle-question'
		},
		ready: {
			bar: 'bg-success-500',
			text: 'text-success-700-300',
			border: 'border-success-500',
			icon: 'fa-solid fa-circle-check'
		},
		excluded: {
			bar: 'bg-surface-400',
			text: 'text-surface-600-400',
			border: 'border-surface-400',
			icon: 'fa-solid fa-circle-minus'
		},
		no_guidance: {
			bar: 'bg-surface-300',
			text: 'text-surface-600-400',
			border: 'border-surface-400',
			icon: 'fa-solid fa-circle-question'
		}
	};
	const VERDICT: Record<Readiness, () => string> = {
		gap: m.prereadVerdictGap,
		weak: m.prereadVerdictWeak,
		to_confirm: m.prereadVerdictToConfirm,
		ready: m.prereadVerdictReady,
		excluded: m.prereadVerdictExcluded,
		no_guidance: m.prereadVerdictNoGuidance
	};

	// ?view= opens a tab directly (a journey step lands on the audit sessions).
	const VIEWS = ['req', 'sessions', 'requests', 'interviews'] as const;
	const askedView = page.url.searchParams.get('view') as (typeof VIEWS)[number];
	let view: (typeof VIEWS)[number] = $state(VIEWS.includes(askedView) ? askedView : 'req');
	let readinessFilter: Readiness | 'all' = $state('all');
	let section = $state('all');
	const prep = $derived(data.preread.preparation as Preparation | null);
	// Stage 1 is the document review: the page opens on it.
	let stage: 0 | 1 | 2 = $state(data.preread.preparation?.stage === 'stage_1' ? 1 : 0);
	let query = $state('');
	let flagged = $state(false);
	let prepOpen = $state(false);
	let selectedId: string | null = $state(page.url.searchParams.get('req'));
	// Paired just now: stays listed though it no longer matches the readiness filter,
	// until another requirement is picked or the filter changes.
	let kept: string | null = $state(null);
	$effect(() => {
		void readinessFilter;
		kept = null;
	});
	let copied = $state(false);
	let listEl: HTMLElement | undefined = $state();

	const counts = $derived(
		Object.fromEntries(
			(Object.keys(READINESS) as Readiness[]).map((r) => [
				r,
				items.filter((i) => i.readiness === r).length
			])
		) as Record<Readiness, number>
	);
	const isFlagged = (i: PrereadItem) => i.prior_findings.some((f) => f.open);
	// Where to start: each step shows only while it has something left to do.
	const onSite = $derived(!!prep?.stage && prep.stage !== 'stage_1');
	const start = $derived.by(() => {
		const open = (i: PrereadItem) => ['gap', 'weak', 'to_confirm'].includes(i.readiness);
		return {
			confirm: counts.to_confirm,
			findings: items.filter(isFlagged).length,
			documents: requestList(items)
				.filter(
					(r) => r.kind !== 'observation' && !r.filed?.length && !r.toConfirm && r.items.length > 1
				)
				.sort((a, b) => b.items.length - a.items.length)
				.slice(0, 3),
			stage1: onSite
				? 0
				: items.filter((i) => open(i) && i.guidance?.questions.some((q) => q.stage === 1)).length,
			sessions: onSite
				? (data.preread.sessions ?? []).filter((x: Session) => !prep?.sessions[x.id]?.date).length
				: 0,
			// The session with the most left to do, to prepare first.
			walk:
				(data.preread.sessions ?? [])
					.map((x: Session) => ({ session: x as Session, count: toDoIn(x) }))
					.filter((w: { count: number }) => w.count)
					.sort((a: { count: number }, b: { count: number }) => b.count - a.count)[0] ?? null
		};
	});
	const matchesQuery = (i: PrereadItem) => {
		const q = query.trim().toLowerCase();
		return !q || i.ref_id.toLowerCase().includes(q) || i.name.toLowerCase().includes(q);
	};
	// Section counts ignore the section filter itself, so each chip says what it would show.
	// Several requirements of a projected framework share one entry (4.2 a, 4.2 b).
	const lettered = $derived.by(() => {
		const keys = items.map((i) => i.guide_key).filter(Boolean);
		return new Set(keys).size < keys.length;
	});
	// Session by session: its requirements still to work on, worst first, one at a time.
	let walkId: string | null = $state(page.url.searchParams.get('session'));
	const TO_DO: Readiness[] = ['gap', 'weak', 'to_confirm'];
	const walkSession = $derived(
		(data.preread.sessions ?? []).find((x: Session) => x.id === walkId) as Session | undefined
	);
	const toDoIn = (x: Session) =>
		items.filter((i) => x.members.includes(keyOf(i)) && TO_DO.includes(i.readiness)).length;
	const beforeSection = $derived(
		items.filter(
			(i) =>
				(!walkSession ||
					(walkSession.members.includes(keyOf(i)) &&
						(TO_DO.includes(i.readiness) || i.id === kept))) &&
				(readinessFilter === 'all' || i.readiness === readinessFilter || i.id === kept) &&
				(!stage || i.guidance?.questions.some((q) => q.stage === stage)) &&
				(!flagged || isFlagged(i)) &&
				matchesQuery(i)
		)
	);
	const visible = $derived.by(() => {
		const shown = beforeSection.filter(
			(i) => section === 'all' || SECTIONS.find((s) => s.key === section)!.test(keyOf(i))
		);
		return walkSession
			? [...shown].sort((a, b) => READINESS[a.readiness].rank - READINESS[b.readiness].rank)
			: shown;
	});
	const grouped = $derived(
		SECTIONS.map((s) => ({ ...s, items: visible.filter((i) => s.test(keyOf(i))) })).filter(
			(g) => g.items.length
		)
	);
	const selectedIndex = $derived(
		Math.max(
			0,
			visible.findIndex((i) => i.id === selectedId)
		)
	);
	const selected = $derived(visible[selectedIndex]);
	// Preparing a session: once the requirement on screen is handled, show its new
	// verdict for a moment, then move on to the next one still to work on.
	$effect(() => {
		if (!walkSession || !selected || TO_DO.includes(selected.readiness)) return;
		const done = selected.id;
		const t = setTimeout(() => {
			const next = visible.find((i) => i.id !== done && TO_DO.includes(i.readiness));
			kept = null;
			if (next) select(next.id);
		}, 1500);
		return () => clearTimeout(t);
	});
	const requests = $derived(requestList(visible));
	const interviews = $derived(interviewPlan(visible));
	const sessions = $derived(sessionPlan(visible, data.preread.sessions ?? []));
	const filtered = $derived(
		readinessFilter !== 'all' || section !== 'all' || stage !== 0 || flagged || query.trim() !== ''
	);

	async function select(id: string, focus = false) {
		if (id !== kept) kept = null;
		selectedId = id;
		const url = new URL(page.url.href);
		url.searchParams.set('req', id);
		if (walkId) url.searchParams.set('session', walkId);
		else url.searchParams.delete('session');
		replaceState(url, {});
		await tick();
		const row = listEl?.querySelector<HTMLElement>(`[data-id="${id}"]`);
		row?.scrollIntoView({ block: 'nearest' });
		if (focus) row?.focus();
	}

	function step(delta: number, focus = false) {
		const next = visible[selectedIndex + delta];
		if (next) select(next.id, focus);
	}

	function onListKey(e: KeyboardEvent) {
		if (e.key === 'ArrowDown' || e.key === 'j') step(1, true);
		else if (e.key === 'ArrowUp' || e.key === 'k') step(-1, true);
		else return;
		e.preventDefault();
	}

	function openRequirement(id: string) {
		clearFilters();
		view = 'req';
		select(id);
	}

	/** Prepare one session (or go back to the full view with null), from its worst requirement. */
	function walk(id: string | null) {
		clearFilters();
		walkId = id;
		view = 'req';
		// Leaving keeps the requirement on screen; entering starts at the worst one.
		const first = (!id && visible.find((i) => i.id === selectedId)) || visible[0];
		if (first) select(first.id);
		else {
			const url = new URL(page.url.href);
			if (id) url.searchParams.set('session', id);
			else url.searchParams.delete('session');
			replaceState(url, {});
		}
	}

	function clearFilters() {
		readinessFilter = 'all';
		section = 'all';
		stage = 0;
		flagged = false;
		query = '';
	}

	const stepNo = (k: number) =>
		[
			start.confirm,
			start.findings,
			start.documents.length,
			start.stage1,
			start.sessions,
			start.walk?.count ?? 0
		]
			.slice(0, k + 1)
			.filter(Boolean).length;

	/** The audit's edit form for one requirement; Cancel and Save come back to it here. */
	function editHref(id: string, tab?: string, focus?: string) {
		const back = new URL(page.url.href);
		back.searchParams.set('req', id);
		return `/requirement-assessments/${id}/edit?next=${encodeURIComponent(back.pathname + back.search)}${tab ? `&tab=${tab}` : ''}${focus ? `&focus=${focus}` : ''}`;
	}

	async function showPrep() {
		prepOpen = true;
		await tick();
		document.getElementById('prep')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}

	const ACTION = {
		evidence: { label: m.prereadActionEvidence, icon: 'fa-solid fa-paperclip' },
		assess: { label: m.prereadActionAssess, icon: 'fa-solid fa-pen' },
		justify: { label: m.prereadActionJustify, icon: 'fa-solid fa-pen' },
		prep: { label: m.prereadActionPrep, icon: 'fa-solid fa-comments' }
	};

	/** Run a start step: show only what it is about, on the requirement view. */
	function go(set: () => void) {
		clearFilters();
		set();
		view = 'req';
	}

	async function copyRequests() {
		try {
			await navigator.clipboard.writeText(requestListTsv(requests));
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			copied = false;
		}
	}

	// Each action shows only to who may do it; the backend enforces it anyway.
	const domain = data.audit.folder?.id;
	const allowed = (codename: string) =>
		!!domain && isAccessAllowed(page.data.user, codename, domain);
	// Pairing, set-asides and the plan are preparation work; the first one creates it.
	const canPrepare = $derived(
		allowed('change_auditpreparation') && (!!prep || allowed('add_auditpreparation'))
	);
	const canEditRA = $derived(allowed('change_requirementassessment'));
	// Set-asides of the domain's previous audit, offered until this one has its own.
	const previous: { reason: string }[] = $derived(
		canPrepare ? (data.preread.previous_set_asides ?? []) : []
	);
	const canUpload = $derived(canPrepare && canEditRA && allowed('add_evidence'));
	// The evidence may sit in another domain; the server checks the real one.
	const canAddFile = $derived(hasPermissionAnywhere(page.data.user, 'add_evidencerevision'));
	const ISSUE: Record<string, string> = {
		unusable: 'text-error-600-400',
		to_validate: 'text-warning-700-300',
		expires_before_audit: 'text-warning-700-300'
	};
	// A hidden evidence comes with its verdict only, not its status or dates.
	const HIDDEN_ISSUE: Record<string, () => string> = {
		unusable: m.prereadHiddenUnusable,
		to_validate: m.prereadHiddenToValidate,
		expires_before_audit: m.prereadHiddenExpires
	};
	// Past tense once the backend judged it lapsed by date.
	const expiryLabel = (e: {
		issue?: string | null;
		status?: string | null;
		expiry_date: string | null;
	}) =>
		(e.issue === 'unusable' && !['rejected', 'missing'].includes(e.status ?? '')
			? m.prereadExpiredOn
			: m.prereadExpires)({ date: new Date(e.expiry_date ?? '').toLocaleDateString(getLocale()) });
	function reachText(r: { requirements: string[]; audits: number }) {
		const parts = [];
		if (r.requirements.length)
			parts.push(
				r.requirements.slice(0, 3).join(', ') +
					(r.requirements.length > 3 ? ` +${r.requirements.length - 3}` : '')
			);
		if (r.audits) parts.push(m.prereadReachAudits({ count: r.audits }));
		return parts.join(', ');
	}

	let pairing: string | null = $state(null);
	const toastStore = getToastStore();
	const modalStore = getModalStore();

	// "Choose an existing document": one picker open at a time, searching every evidence the user sees.
	let picking: { key: string; ra: string; request: string } | null = $state(null);
	const pickSchema = z.object({ evidence: z.string().nullable().optional() });
	const pickForm = superForm(defaults({ evidence: null }, zod(pickSchema)), {
		dataType: 'json',
		taintedMessage: false,
		SPA: true,
		validators: zod(pickSchema)
	});
	const pickValue = pickForm.form;
	function togglePick(key: string, ra: string, request: string) {
		picking = picking?.key === key ? null : { key, ra, request };
		pickForm.reset();
	}
	$effect(() => {
		const evidence = $pickValue.evidence;
		if (evidence && picking) pick(picking.ra, picking.request, evidence, true);
	});
	async function pick(raId: string, request: string, evidence: string, attach = false) {
		picking = null;
		pickForm.reset();
		await pair(raId, request, evidence, false, attach);
	}

	/** Store one decision of the preparation; true when saved. */
	async function savePrep(body: Record<string, unknown>) {
		const res = await fetch(`/experimental/auditor-preread/${data.audit.id}/preparation`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		if (!res.ok) {
			toastStore.trigger({
				message: res.status === 403 ? m.prereadCannotEdit() : m.prereadNotSaved(),
				background: 'preset-filled-error-500'
			});
			return false;
		}
		await invalidateAll();
		return true;
	}

	// One editor open at a time: the audit panel, a role or a session.
	const prepSchema = z.object({
		body: z.string().nullable().optional(),
		actors: z.array(z.string()).optional()
	});
	const prepForm = superForm(defaults({ body: null, actors: [] }, zod(prepSchema)), {
		dataType: 'json',
		taintedMessage: false,
		SPA: true,
		validators: zod(prepSchema)
	});
	const prepValue = prepForm.form;
	let editing: { kind: 'audit' | 'role' | 'session'; key: string } | null = $state(null);
	let draft = $state({ stage: '', start_date: '', end_date: '', auditors: '' });
	let slot = $state({ date: '', start_time: '', end_time: '', location: '' });
	const ids = (list?: ActorRef[]) => (list ?? []).map((a) => a.id);
	function edit(kind: 'audit' | 'role' | 'session', key = '') {
		editing = { kind, key };
		const s = prep?.sessions[key];
		draft = {
			stage: prep?.stage ?? '',
			start_date: prep?.start_date ?? '',
			end_date: prep?.end_date ?? '',
			auditors: prep?.auditors ?? ''
		};
		slot = {
			date: s?.date ?? '',
			start_time: s?.start_time?.slice(0, 5) ?? '',
			end_time: s?.end_time?.slice(0, 5) ?? '',
			location: s?.location ?? ''
		};
		prepForm.reset({
			data: {
				body: prep?.certification_body?.id ?? null,
				actors: kind === 'role' ? ids(prep?.roles[key]) : ids(s?.attendees)
			}
		});
	}
	async function saveEdit() {
		if (!editing) return;
		const { kind, key } = editing;
		const body =
			kind === 'audit'
				? { fields: { ...draft, certification_body: $prepValue.body ?? null } }
				: kind === 'role'
					? { role: { role: key, actors: $prepValue.actors ?? [] } }
					: { session: { session: key, ...slot, attendees: $prepValue.actors ?? [] } };
		if (await savePrep(body)) editing = null;
	}

	// "Doesn't apply": one reason box open at a time.
	let asideFor: string | null = $state(null);
	let asideReason = $state('');
	async function setAside(ra: string, request: string, remove = false) {
		const body = { requirement_assessment: ra, request, reason: asideReason, remove };
		if (await savePrep({ set_aside: body })) {
			asideFor = null;
			asideReason = '';
			kept = ra;
		}
	}

	/** A file or link for a paired evidence that has neither: a new revision of it. */
	function addFile(evidence: string) {
		const f = data.revisionCreateForm;
		modalStore.trigger({
			type: 'component',
			component: {
				ref: CreateModal,
				props: {
					form: { ...f, id: `preread-revision-${evidence}`, data: { ...f.data, evidence } },
					formAction: '?/createRevision',
					model: data.revisionModel,
					debug: false
				}
			},
			title: m.prereadAddFile()
		});
	}

	/** New evidence for one request: created on the requirement and paired with the request. */
	function upload(raId: string, r: { id: string; label: string }) {
		const f = data.evidenceCreateForm;
		const guide = page.url.searchParams.get('guide');
		kept = raId;
		modalStore.trigger({
			type: 'component',
			component: {
				ref: CreateModal,
				props: {
					form: {
						...f,
						id: `preread-evidence-${raId}-${r.id}`,
						data: { ...f.data, name: r.label, requirement_assessments: [raId] }
					},
					formAction: `?/createEvidence&ra=${raId}&request=${encodeURIComponent(r.id)}${guide ? `&guide=${encodeURIComponent(guide)}` : ''}`,
					model: data.evidenceModel,
					debug: false
				}
			},
			title: m.prereadUpload()
		});
	}

	/** Mark (or unmark) an evidence as answering one request, then reload the pre-read. */
	async function pair(
		raId: string,
		request: string,
		evidence: string,
		remove = false,
		attach = false
	) {
		pairing = `${request}:${evidence}`;
		const guide = page.url.searchParams.get('guide');
		const res = await fetch(`/experimental/auditor-preread/${data.audit.id}/pair`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				requirement_assessment: raId,
				request,
				evidence,
				remove,
				attach,
				guide
			})
		});
		if (res.ok) {
			kept = raId;
			await invalidateAll();
		} else
			toastStore.trigger({
				message: res.status === 403 ? m.prereadCannotEdit() : m.prereadPairNotSaved(),
				background: 'preset-filled-error-500'
			});
		pairing = null;
	}

	const pct = (n: number) => (items.length ? (100 * n) / items.length : 0);
	const ageLabel = (iso: string | null) => (iso ? iso.slice(0, 10) : m.prereadNoRevision());
</script>

{#snippet dot(r: Readiness)}
	<span
		class="inline-block w-2 h-2 rounded-full shrink-0 {STYLE[r].bar}"
		title={READINESS[r].label}
		aria-label={READINESS[r].label}
	></span>
{/snippet}

{#snippet title(icon: string, label: string, aside = '')}
	<h3 class="flex items-baseline gap-2 text-base font-semibold">
		<i class="{icon} text-primary-500 w-4 text-center text-sm"></i>{label}
		{#if aside}<span class="text-sm font-normal text-surface-500">{aside}</span>{/if}
	</h3>
{/snippet}

{#snippet heading(icon: string, label: string)}
	<h3
		class="flex items-center gap-2 text-xs uppercase tracking-wider text-surface-600-400 font-semibold"
	>
		<i class="{icon} w-4 text-center"></i>{label}
	</h3>
{/snippet}

<div class="p-4 md:p-6 flex flex-col gap-5">
	<!-- Summary -->
	<header
		class="card border border-surface-200-800 overflow-hidden flex flex-col"
		aria-label={m.prereadSummary()}
	>
		<div class="h-1 bg-gradient-to-r from-primary-500 via-primary-400 to-secondary-400"></div>
		<div class="p-5 flex flex-col gap-4">
			<div class="flex flex-wrap items-center gap-x-3 gap-y-1">
				<span
					class="grid place-items-center w-8 h-8 rounded-full bg-primary-500/10 text-primary-600-400"
				>
					<i class="fa-solid fa-user-tie"></i>
				</span>
				<div class="flex flex-col leading-tight">
					<span class="text-xs uppercase tracking-[0.12em] font-semibold text-primary-600-400"
						>{m.prereadTitle()}</span
					>
					<span class="text-sm text-surface-600-400">{data.audit.framework?.str ?? ''}</span>
				</div>
				<a
					href="/compliance-assessments/{data.audit.id}"
					class="btn btn-sm preset-tonal-surface ml-auto"
				>
					<i class="fa-solid fa-arrow-up-right-from-square"></i>{m.prereadOpenAudit()}
				</a>
			</div>
			{#if data.preread.supported}
				{@const stageLabel = prep?.stage ? safeTranslate(`prereadStage_${prep.stage}`) : ''}
				{@const dates = [prep?.start_date, prep?.end_date]
					.filter(Boolean)
					.map((d) => new Date(d!).toLocaleDateString(getLocale()))
					.join(' – ')}
				<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
					<i class="fa-solid fa-calendar-check text-surface-500"></i>
					<span class={stageLabel || dates ? '' : 'text-surface-600-400'}
						>{[stageLabel, dates, prep?.certification_body?.str, prep?.auditors]
							.filter(Boolean)
							.join(' · ') || m.prereadPrepNone()}</span
					>
					{#if canPrepare}
						<button
							class="btn btn-sm preset-tonal-primary"
							aria-expanded={editing?.kind === 'audit'}
							onclick={() => (editing?.kind === 'audit' ? (editing = null) : edit('audit'))}
							><i class="fa-solid fa-pen"></i>{m.prereadPrepare()}</button
						>
					{/if}
				</div>
				{#if editing?.kind === 'audit'}
					<div
						class="rounded-base border border-surface-200-800 bg-surface-50-950 p-4 grid gap-3 md:grid-cols-2"
					>
						<label class="flex flex-col gap-1 text-sm"
							><span class="font-medium">{m.prereadStageField()}</span>
							<select class="select" bind:value={draft.stage}>
								<option value="">{m.prereadStageNone()}</option>
								{#each ['stage_1', 'stage_2', 'surveillance', 'recertification'] as v (v)}
									<option value={v}>{safeTranslate(`prereadStage_${v}`)}</option>
								{/each}
							</select>
						</label>
						<label class="flex flex-col gap-1 text-sm"
							><span class="font-medium">{m.prereadAuditors()}</span>
							<input class="input" type="text" bind:value={draft.auditors} />
						</label>
						<label class="flex flex-col gap-1 text-sm"
							><span class="font-medium">{m.prereadFirstDay()}</span>
							<input class="input" type="date" bind:value={draft.start_date} />
						</label>
						<label class="flex flex-col gap-1 text-sm"
							><span class="font-medium">{m.prereadLastDay()}</span>
							<input class="input" type="date" bind:value={draft.end_date} />
							<span class="text-xs text-surface-600-400">{m.prereadLastDayHint()}</span>
						</label>
						<div class="md:col-span-2">
							<AutocompleteSelect
								form={prepForm}
								field="body"
								optionsEndpoint="entities"
								nullable
								label={m.prereadCertificationBody()}
							/>
						</div>
						<div class="md:col-span-2 flex justify-end gap-2">
							<button class="btn btn-sm preset-tonal-surface" onclick={() => (editing = null)}
								>{m.cancel()}</button
							>
							<button class="btn btn-sm preset-filled-primary-500" onclick={saveEdit}
								>{m.save()}</button
							>
						</div>
					</div>
				{/if}
			{/if}

			{#if data.preread.supported && items.length}
				<div class="flex flex-col gap-2">
					<div
						class="flex h-2 w-full gap-0.5 overflow-hidden rounded-full"
						role="img"
						aria-label={SHOWN.map((r) => `${counts[r]} ${READINESS[r].label}`).join(', ')}
						title={m.prereadSummaryHint({ count: items.length })}
					>
						{#each SHOWN as r (r)}
							{#if counts[r]}
								<span class={STYLE[r].bar} style="width: {pct(counts[r])}%"></span>
							{/if}
						{/each}
					</div>
					<div class="flex flex-wrap gap-1.5 text-sm" role="group" aria-label={m.prereadSummary()}>
						{#each SHOWN as r (r)}
							{@const on = readinessFilter === r}
							<button
								class="flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 disabled:opacity-50 disabled:cursor-default {on
									? `bg-surface-100-900 font-medium ${STYLE[r].border}`
									: 'border-surface-200-800 enabled:hover:bg-surface-100-900'}"
								aria-pressed={on}
								disabled={!counts[r] && !on}
								title={on ? m.prereadShowAll() : m.prereadShowOnly({ state: READINESS[r].label })}
								onclick={() => (readinessFilter = on ? 'all' : r)}
							>
								{@render dot(r)}<span class="font-semibold tabular-nums">{counts[r]}</span>
								<span class="text-surface-600-400">{READINESS[r].label}</span>
								{#if on}<i class="fa-solid fa-xmark text-xs" aria-hidden="true"></i>{/if}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</header>

	{#if data.preread.supported && (start.confirm || start.findings || start.documents.length || start.stage1 || start.sessions || start.walk || previous.length)}
		<section
			class="card border border-primary-500/40 bg-primary-500/5 p-4 flex flex-col gap-2"
			aria-label={m.prereadStartTitle()}
		>
			<h2 class="font-semibold flex items-center gap-2">
				<i class="fa-solid fa-route text-primary-500"></i>{m.prereadStartTitle()}
			</h2>
			<ol class="flex flex-col gap-1.5 text-sm">
				{#if start.confirm}
					<li class="flex gap-2">
						<span class="text-surface-500 tabular-nums">{stepNo(0)}.</span>
						<button
							class="anchor text-left"
							onclick={() => go(() => (readinessFilter = 'to_confirm'))}
							>{m.prereadStartConfirm({ count: start.confirm })}</button
						>
					</li>
				{/if}
				{#if start.findings}
					<li class="flex gap-2">
						<span class="text-surface-500 tabular-nums">{stepNo(1)}.</span>
						<button class="anchor text-left" onclick={() => go(() => (flagged = true))}
							>{m.prereadStartFindings({ count: start.findings })}</button
						>
					</li>
				{/if}
				{#if start.documents.length}
					<li class="flex gap-2">
						<span class="text-surface-500 tabular-nums">{stepNo(2)}.</span>
						<div class="flex flex-col gap-1">
							<span>{m.prereadStartDocuments()}</span>
							<ul class="flex flex-col gap-0.5">
								{#each start.documents as r, i (i)}
									<li class="flex flex-wrap items-baseline gap-x-2">
										<i class="{KINDS[r.kind]?.icon ?? 'fa-solid fa-file'} text-surface-500 text-xs"
										></i>
										<button class="anchor text-left" onclick={() => openRequirement(r.items[0].id)}
											>{r.label}</button
										>
										<span class="text-xs text-surface-600-400"
											>{m.prereadAnswers({ count: r.items.length })}</span
										>
									</li>
								{/each}
							</ul>
							<button
								class="anchor text-left text-xs"
								onclick={() => {
									clearFilters();
									view = 'requests';
								}}>{m.prereadSeeAllRequests()}</button
							>
						</div>
					</li>
				{/if}
				{#if start.stage1}
					<li class="flex gap-2">
						<span class="text-surface-500 tabular-nums">{stepNo(3)}.</span>
						<button class="anchor text-left" onclick={() => go(() => (stage = 1))}
							>{m.prereadStartStage1({ count: start.stage1 })}</button
						>
					</li>
				{/if}
				{#if start.sessions}
					<li class="flex gap-2">
						<span class="text-surface-500 tabular-nums">{stepNo(4)}.</span>
						<button class="anchor text-left" onclick={() => (view = 'sessions')}
							>{m.prereadStartSessions({ count: start.sessions })}</button
						>
					</li>
				{/if}
				{#if start.walk}
					<li class="flex gap-2">
						<span class="text-surface-500 tabular-nums">{stepNo(5)}.</span>
						<button class="anchor text-left" onclick={() => walk(start.walk!.session.id)}
							>{m.prereadStartWalk({
								label: start.walk.session.label,
								count: start.walk.count
							})}</button
						>
					</li>
				{/if}
			</ol>
			{#if previous.length}
				<p class="text-sm flex flex-wrap items-center gap-2">
					<i class="fa-solid fa-clock-rotate-left text-surface-500"></i>
					<span title={previous.map((a: { reason: string }) => a.reason).join('\n')}
						>{m.prereadCarryOver({ count: previous.length })}</span
					>
					<button
						class="btn btn-sm preset-tonal-primary"
						onclick={() => savePrep({ carry_over: true })}>{m.prereadCarryOverAction()}</button
					>
				</p>
			{/if}
		</section>
	{/if}

	{#if !data.preread.supported}
		<div class="card preset-tonal-warning p-4 flex flex-col gap-2">
			<p>
				{m.prereadUnsupported()}
			</p>
			{#if data.preread.suggestion}
				{@const s = data.preread.suggestion}
				<p class="text-sm">
					{m.prereadSuggestion({
						guide: s.name,
						pct: Math.round(s.coverage * 100),
						matched: s.matched,
						total: s.total
					})}
					<!-- Stored on the preparation, so every later save and visit uses it; a
					     reader who cannot prepare only gets it for this visit. -->
					{#if canPrepare}
						<button class="anchor" onclick={() => savePrep({ fields: { guide: s.urn } })}
							>{m.prereadApplyAnyway()}</button
						>
					{:else}
						<a class="anchor" href="?guide={encodeURIComponent(s.urn)}">{m.prereadApplyAnyway()}</a>
					{/if}
				</p>
			{/if}
		</div>
	{:else}
		{#if data.preread.guide && !data.preread.guide.exact}
			<p class="text-sm text-surface-600-400 flex items-center gap-2">
				<i class="fa-solid fa-shuffle"></i>
				{m.prereadProjected({
					matched: data.preread.guide.matched,
					total: data.preread.guide.total
				})}
				{#if lettered}{m.prereadLettered()}{/if}
			</p>
		{/if}
		{#if walkSession}
			<div
				class="card border border-primary-500/40 bg-primary-500/5 p-3 flex flex-wrap items-center gap-x-3 gap-y-1"
			>
				<i class="fa-solid fa-shoe-prints text-primary-500"></i>
				<span class="font-semibold">{m.prereadWalkSession({ label: walkSession.label })}</span>
				<span class="text-sm text-surface-600-400"
					>{m.prereadWalkCount({ count: toDoIn(walkSession) })}</span
				>
				<button class="btn btn-sm preset-tonal-surface ml-auto" onclick={() => walk(null)}
					><i class="fa-solid fa-xmark"></i>{m.prereadWalkExit()}</button
				>
			</div>
		{:else}
			<!-- Tabs -->
			<div class="flex gap-1 border-b border-surface-200-800 overflow-x-auto" role="tablist">
				{#each [['req', m.prereadByRequirement(), 'fa-solid fa-list-check', visible.length], ['sessions', m.prereadSessions(), 'fa-solid fa-calendar-day', sessions.length], ['requests', m.prereadRequestList(), 'fa-solid fa-folder-open', requests.length], ['interviews', m.prereadInterviewPlan(), 'fa-solid fa-people-group', interviews.length]] as const as [key, label, icon, n] (key)}
					<button
						role="tab"
						aria-selected={view === key}
						class="flex items-center gap-2 px-3 py-2 -mb-px border-b-2 whitespace-nowrap {view ===
						key
							? 'border-primary-500 font-semibold'
							: 'border-transparent text-surface-600-400 hover:text-surface-950-50'}"
						onclick={() => (view = key)}
					>
						<i class={icon}></i>{label}
						<span class="badge preset-tonal-surface text-xs tabular-nums">{n}</span>
					</button>
				{/each}
			</div>

			<!-- Filters -->
			<div class="flex flex-wrap items-center gap-2">
				<label class="relative grow max-w-sm">
					<span class="sr-only">{m.prereadSearchRequirements()}</span>
					<i
						class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-surface-500 text-sm"
					></i>
					<input
						class="input pl-9 w-full"
						type="search"
						placeholder={m.prereadSearchRequirementsPlaceholder()}
						bind:value={query}
					/>
				</label>
				<div
					class="flex rounded-base border border-surface-200-800 overflow-hidden text-sm"
					role="group"
					aria-label={m.prereadAuditStage()}
				>
					{#each [[0, m.prereadBothStages()], [1, m.prereadStage1()], [2, m.prereadStage2()]] as [value, label] (value)}
						<button
							class="px-3 py-1.5 {stage === value
								? 'preset-filled-primary-500'
								: 'hover:bg-surface-100-900'}"
							aria-pressed={stage === value}
							title={value ? STAGES[value as number] : m.prereadBothStagesHint()}
							onclick={() => (stage = value as 0 | 1 | 2)}>{label}</button
						>
					{/each}
				</div>
				<label>
					<span class="sr-only">{m.prereadSection()}</span>
					<select class="select w-auto text-sm py-1.5" bind:value={section}>
						{#each [{ key: 'all', label: m.prereadAllSections(), test: () => true }, ...SECTIONS.filter( (s) => data.preread.items.some( (i: any) => s.test(keyOf(i)) ) )] as s (s.key)}
							<option value={s.key}
								>{s.label} ({beforeSection.filter((i) => s.test(keyOf(i))).length})</option
							>
						{/each}
					</select>
				</label>
				{#if flagged}
					<button
						class="flex items-center gap-1.5 rounded-full border border-error-500 px-2.5 py-0.5 text-sm"
						aria-pressed="true"
						onclick={() => (flagged = false)}
					>
						<i class="fa-solid fa-flag text-error-500 text-xs"></i>{m.prereadOpenFindingsFilter()}
						<i class="fa-solid fa-xmark text-xs" aria-hidden="true"></i>
					</button>
				{/if}
				{#if filtered}
					<button class="btn btn-sm preset-tonal-surface" onclick={clearFilters}>
						<i class="fa-solid fa-xmark"></i>{m.prereadClearFilters()}
					</button>
				{/if}
			</div>
		{/if}

		{#if view === 'req'}
			<div
				class="grid grid-cols-1 gap-5 items-start {walkSession
					? ''
					: 'lg:grid-cols-[20rem_minmax(0,1fr)]'}"
			>
				<!-- Requirement index; none while preparing a session: one requirement at a time -->
				{#if !walkSession}
					<nav
						bind:this={listEl}
						class="card border border-surface-200-800 lg:sticky lg:top-4 max-h-[75vh] overflow-auto"
						aria-label={m.prereadRequirements()}
					>
						{#each grouped as g (g.key)}
							<div
								class="sticky top-0 z-10 bg-surface-50-950 px-3 py-1.5 text-xs uppercase tracking-wider font-semibold text-surface-600-400 border-b border-surface-200-800 flex justify-between"
							>
								<span>{g.label}</span><span class="tabular-nums">{g.items.length}</span>
							</div>
							<ul aria-label={g.label}>
								{#each g.items as item (item.id)}
									<li>
										<button
											data-id={item.id}
											aria-current={selected?.id === item.id}
											onkeydown={onListKey}
											tabindex={selected?.id === item.id ? 0 : -1}
											class="w-full grid grid-cols-[3.75rem_1fr_auto] gap-2 items-center text-left px-3 py-2 text-sm border-l-2 {selected?.id ===
											item.id
												? 'bg-primary-500/10 border-primary-500'
												: 'border-transparent hover:bg-surface-100-900'}"
											onclick={() => select(item.id)}
										>
											<span class="font-mono text-xs text-surface-600-400">{item.ref_id}</span>
											<span class="leading-snug"
												>{item.name}{#if item.prior_findings.some((f) => f.open)}<i
														class="fa-solid fa-flag text-error-500 text-xs ml-1.5"
														title={m.prereadOpenFindingHint()}
													></i>{/if}</span
											>
											{@render dot(item.readiness)}
										</button>
									</li>
								{/each}
							</ul>
						{:else}
							<div class="p-6 text-center text-sm text-surface-600-400 flex flex-col gap-2">
								<i class="fa-solid fa-filter-circle-xmark text-2xl"></i>
								{m.prereadNothingMatches()}
								<button class="anchor" onclick={clearFilters}>{m.prereadClearFilters()}</button>
							</div>
						{/each}
					</nav>
				{/if}

				<!-- Requirement file -->
				{#if walkSession && !selected}
					<div class="card border border-surface-200-800 p-6 flex flex-col items-start gap-3">
						<p>
							<i class="fa-solid fa-circle-check text-success-500 mr-2"></i>{m.prereadWalkDone()}
						</p>
						<button class="btn btn-sm preset-filled-primary-500" onclick={() => walk(null)}
							>{m.prereadWalkExit()}</button
						>
					</div>
				{:else if selected}
					{@const g = selected.guidance}
					{@const s = STYLE[selected.readiness]}
					{@const steps = todos(selected)}
					<article class="card border border-surface-200-800 flex flex-col min-w-0">
						<header
							class="flex flex-wrap items-start gap-x-3 gap-y-2 p-5 border-b border-surface-200-800"
						>
							<div class="flex flex-col gap-1 min-w-0 grow">
								<span class="text-xs text-surface-600-400">{sectionOf(keyOf(selected)).label}</span>
								<h2 class="text-xl font-semibold leading-tight">
									<span class="font-mono text-primary-600-400 mr-2">{selected.ref_id}</span
									>{selected.name}
								</h2>
							</div>
							<div class="flex items-center gap-2">
								{#if selected.result}<span
										class="text-xs text-surface-600-400"
										title={m.prereadResultHint()}
									>
										{m.prereadResultIn({ result: safeTranslate(selected.result) })}
									</span>{/if}
								{#if canEditRA}
									<a
										class="btn btn-sm preset-tonal-primary"
										href={editHref(selected.id)}
										title={m.prereadOpenInAuditHint()}
									>
										<i class="fa-solid fa-arrow-up-right-from-square"></i>{m.prereadOpenInAudit()}
									</a>
								{/if}
							</div>
						</header>

						<div class="p-5 flex flex-col gap-6">
							{#if !canPrepare}
								<p class="text-sm text-surface-600-400">
									<i class="fa-solid fa-eye mr-1"></i>{m.prereadReadOnly()}
								</p>
							{/if}
							<!-- Verdict -->
							<div class="rounded-base bg-surface-100-900 border-l-4 p-4 flex gap-3 {s.border}">
								<i class="{s.icon} {s.text} text-xl mt-0.5"></i>
								<div class="flex flex-col gap-2 min-w-0">
									<p>
										<span class="font-semibold {s.text}"
											>{READINESS[selected.readiness].label}.</span
										>
										{VERDICT[selected.readiness]()}
									</p>
									{#if steps.length}
										<div class="flex flex-col gap-1.5">
											<span
												class="text-xs uppercase tracking-wider font-semibold text-surface-600-400"
												>{m.prereadTodoTitle()}</span
											>
											<ol class="flex flex-col gap-2">
												{#each steps as t, n (n)}
													<li class="flex flex-wrap items-center gap-x-3 gap-y-1">
														<span
															class="size-5 shrink-0 rounded-full bg-surface-200-800 grid place-items-center text-xs font-semibold tabular-nums"
															>{n + 1}</span
														>
														<span class="grow basis-64">{t.text}</span>
														{#if t.action === 'prep'}
															<button class="btn btn-sm preset-tonal-primary" onclick={showPrep}
																><i class={ACTION.prep.icon}></i>{ACTION.prep.label()}</button
															>
														{:else if t.action && canEditRA}
															<a
																class="btn btn-sm preset-tonal-primary"
																href={editHref(
																	selected.id,
																	t.action === 'evidence' ? 'evidences' : undefined,
																	t.action === 'evidence' ? undefined : 'result'
																)}
																><i class={ACTION[t.action].icon}></i>{ACTION[t.action].label()}</a
															>
														{/if}
													</li>
												{/each}
											</ol>
										</div>
									{/if}
									{#if selected.findings.length}
										<details class="text-sm">
											<summary class="cursor-pointer text-surface-600-400">
												{m.prereadQualityFindings({ count: selected.findings.length })}
											</summary>
											<ul class="mt-1 flex flex-col gap-1 pl-1">
												{#each selected.findings as f, i (i)}
													<li class="flex gap-2">
														<i
															class="fa-solid {f.severity === 'error'
																? 'fa-circle-xmark text-error-500'
																: 'fa-triangle-exclamation text-warning-500'} mt-1 text-xs"
														></i>
														{safeTranslate(f.msgid) === f.msgid ? f.msg : safeTranslate(f.msgid)}
													</li>
												{/each}
											</ul>
										</details>
									{/if}
								</div>
							</div>

							{#if selected.prior_findings.length}
								<section class="flex flex-col gap-2">
									{@render title(
										'fa-solid fa-flag',
										m.prereadEarlierAudit(),
										m.prereadEarlierAuditHint()
									)}
									<ul class="flex flex-col divide-y divide-surface-200-800 text-sm">
										{#each selected.prior_findings as f, n (n)}
											<li class="flex flex-wrap items-baseline gap-x-3 gap-y-1 py-2">
												<i
													class="fa-solid {f.open
														? 'fa-flag text-error-500'
														: 'fa-check text-success-500'} text-xs"
												></i>
												{#if f.id}<a class="anchor grow" href="/findings/{f.id}"
														>{f.ref_id ? `${f.ref_id} ` : ''}{f.name}</a
													>{:else}<span class="grow italic text-surface-600-400"
														>{m.prereadHiddenFinding()}</span
													>{/if}
												<span class="text-xs text-surface-600-400"
													>{safeTranslate(
														['undefined', 'info', 'low', 'medium', 'high', 'critical'][
															f.severity + 1
														] ?? ''
													)} · {safeTranslate(f.status)}{f.source ? ` · ${f.source}` : ''}</span
												>
											</li>
										{/each}
									</ul>
								</section>
							{/if}

							{#if g}
								{@const pairedIds = new Set(
									Object.values(selected.filed ?? {})
										.flat()
										.map((e) => e.id)
								)}
								{@const unpaired = unpairedOf(selected)}
								<!-- Requested vs on file -->
								<section class="flex flex-col gap-3">
									{@render title(
										'fa-solid fa-scale-balanced',
										m.prereadRequestedVsOnFile(),
										m.prereadRequestedAside({
											toFile: g.requests.filter((r) => r.kind !== 'observation').length,
											matched: Object.values(selected.filed ?? {}).filter((f) =>
												f.some((e) => e.has_file)
											).length,
											other: unpaired.length
										})
									)}
									<div
										class="grid grid-cols-1 xl:grid-cols-2 gap-4 rounded-container bg-surface-100-900 p-3"
									>
										<section class="flex flex-col gap-2">
											{@render heading('fa-solid fa-folder-open', m.prereadWillAskFor())}
											<ul
												class="flex flex-col divide-y divide-surface-200-800 border border-surface-200-800 rounded-base bg-surface-50-950"
											>
												{#each g.requests as r (r.id)}
													{@const filed =
														selected.filed?.[r.id] ?? (r.reference_control ? [] : null)}
													{@const candidates =
														r.kind === 'observation'
															? []
															: selected.evidences.filter(
																	(e) => e.name && !filed?.some((f) => f.id === e.id)
																)}
													{@const aside = selected.set_aside?.[r.id]}
													{@const key = `${selected.id}:${r.id}`}
													<li class="flex flex-col gap-1.5 p-2.5 text-sm">
														<span class="flex gap-3">
															<i
																class="{KINDS[r.kind]?.icon ??
																	'fa-solid fa-file'} text-surface-500 mt-0.5 w-4 text-center"
																title={KINDS[r.kind]?.label ?? r.kind}
															></i>
															<span class="grow">{r.label}</span>
															{#if r.fresh_days}
																<span
																	class="shrink-0 text-xs text-surface-600-400 tabular-nums"
																	title={m.prereadFreshHint()}
																	>≤ {m.prereadDays({ days: r.fresh_days })}</span
																>
															{/if}
														</span>
														{#if aside}
															<span class="pl-7 text-xs text-surface-600-400 flex flex-wrap gap-x-2"
																><span
																	><i class="fa-solid fa-ban mr-1"></i>{m.prereadSetAsideShown({
																		reason: aside.reason
																	})}</span
																>{#if canPrepare}<button
																		class="anchor"
																		onclick={() => setAside(selected.id, r.id, true)}
																		>{m.prereadRestore()}</button
																	>{/if}</span
															>
														{:else}
															{#if filed?.length}
																<ul class="pl-7 flex flex-col gap-1 text-xs">
																	{#each filed as e (e.id)}
																		{@const old = e.stale}
																		{@const issue = e.issue}
																		<li class="flex flex-wrap items-baseline gap-x-2">
																			{#if issue === 'no_file' || issue === 'unusable'}
																				<i
																					class="fa-solid fa-triangle-exclamation text-warning-600-400"
																				></i>
																			{:else}
																				<i class="fa-solid fa-check text-success-500"></i>
																			{/if}
																			{#if e.name}<a class="anchor" href="/evidences/{e.id}"
																					>{e.name}</a
																				>{:else}<span class="italic text-surface-600-400"
																					>{m.prereadEvidenceHidden()}</span
																				>{/if}
																			{#if e.name}<span
																					class="tabular-nums {old
																						? 'text-warning-700-300'
																						: 'text-surface-600-400'}"
																					>{#if old}<i class="fa-solid fa-clock-rotate-left mr-1"
																						></i>{/if}{ageLabel(e.updated_at)}</span
																				>{/if}
																			{#if !e.here}<span
																					class="text-surface-600-400"
																					title={m.prereadFiledElsewhereHint()}
																					>{m.prereadFiledElsewhere()}</span
																				>{/if}
																			{#if issue && issue !== 'no_file'}
																				<span class={ISSUE[issue]}
																					>{e.name
																						? safeTranslate(e.status ?? '')
																						: HIDDEN_ISSUE[issue]?.()}{#if e.expiry_date}
																						· {expiryLabel(e)}{/if}</span
																				>
																			{/if}
																			{#if e.has_file === false && e.name && canAddFile}
																				<button
																					class="anchor text-warning-700-300"
																					onclick={() => addFile(e.id)}
																					><i class="fa-solid fa-file-circle-plus mr-1"
																					></i>{m.prereadAddFile()}</button
																				>
																			{/if}
																			{#if e.manual}
																				<span class="text-surface-600-400"
																					>{m.prereadPairedByHand()}</span
																				>
																				{#if canPrepare}<button
																						class="text-surface-500 hover:text-error-600-400 disabled:opacity-50"
																						title={m.prereadUnpairHint()}
																						aria-label={m.prereadUnpair({ name: e.name ?? '' })}
																						disabled={pairing !== null}
																						onclick={() => pair(selected.id, r.id, e.id, true)}
																						><i class="fa-solid fa-xmark"></i></button
																					>{/if}
																				{#if e.reach && (e.reach.requirements.length || e.reach.audits)}
																					<span class="basis-full pl-5 text-surface-600-400"
																						><i class="fa-solid fa-share-nodes mr-1"
																						></i>{m.prereadReach({
																							what: reachText(e.reach)
																						})}</span
																					>
																				{/if}
																			{/if}
																		</li>
																	{/each}
																</ul>
															{:else if r.kind !== 'observation' && unpaired.length}
																<span class="pl-7 text-xs text-primary-700-300"
																	><i class="fa-solid fa-circle-question mr-1"
																	></i>{m.prereadToConfirmPick()}</span
																>
															{:else if r.kind !== 'observation'}
																<span class="pl-7 text-xs text-error-600-400"
																	><i class="fa-solid fa-circle-xmark mr-1"
																	></i>{m.prereadNotOnFile()}</span
																>
															{/if}
															{#if !filed?.length && r.kind !== 'observation' && canPrepare}
																<span class="pl-7 flex flex-wrap gap-2">
																	{#if canUpload}<button
																			class="btn btn-sm preset-tonal-primary"
																			title={m.prereadUploadHint()}
																			onclick={() => upload(selected.id, r)}
																			><i class="fa-solid fa-upload"></i>{m.prereadUpload()}</button
																		>{/if}
																	<button
																		class="btn btn-sm {picking?.key === key
																			? 'preset-filled-primary-500'
																			: 'preset-tonal-primary'}"
																		title={m.prereadPickHint()}
																		aria-expanded={picking?.key === key}
																		onclick={() => togglePick(key, selected.id, r.id)}
																		><i class="fa-solid fa-magnifying-glass"
																		></i>{m.prereadPickExisting()}</button
																	>
																	<button
																		class="btn btn-sm preset-tonal-surface"
																		title={m.prereadSetAsideHint()}
																		aria-expanded={asideFor === key}
																		onclick={() => {
																			asideFor = asideFor === key ? null : key;
																			asideReason = '';
																		}}><i class="fa-solid fa-ban"></i>{m.prereadSetAside()}</button
																	>
																</span>
																{#if asideFor === key}
																	<form
																		class="ml-7 flex flex-wrap gap-2"
																		onsubmit={(ev) => {
																			ev.preventDefault();
																			setAside(selected.id, r.id);
																		}}
																	>
																		<input
																			class="input py-1 text-sm grow basis-64"
																			required
																			placeholder={m.prereadSetAsideReason()}
																			aria-label={m.prereadSetAsideReason()}
																			bind:value={asideReason}
																			{@attach (el) => el.focus()}
																		/>
																		<button
																			class="btn btn-sm preset-filled-primary-500"
																			type="submit">{m.save()}</button
																		>
																	</form>
																{/if}
																{#if picking?.key === key}
																	<div
																		class="ml-7 flex flex-col gap-2 rounded-base border border-surface-200-800 bg-surface-50-950 p-2"
																	>
																		{#if candidates.length}
																			<span class="text-xs text-surface-600-400"
																				>{m.prereadPickOnRequirement()}</span
																			>
																			<span class="flex flex-wrap gap-1.5">
																				{#each candidates as e (e.id)}
																					<button
																						class="btn btn-sm preset-tonal-primary disabled:opacity-50"
																						disabled={pairing !== null}
																						onclick={() => pick(selected.id, r.id, e.id)}
																						>{e.name}</button
																					>
																				{/each}
																			</span>
																		{/if}
																		{#if canEditRA}<AutocompleteSelect
																				form={pickForm}
																				field="evidence"
																				optionsEndpoint="evidences"
																				lazy
																				optionsExtraFields={[['folder', 'str']]}
																				label={m.prereadPickSearch()}
																			/>{/if}
																	</div>
																{/if}
															{/if}
														{/if}
													</li>
												{/each}
											</ul>
										</section>
										<section class="flex flex-col gap-2">
											{@render heading(
												'fa-solid fa-paperclip',
												pairedIds.size ? m.prereadAlsoOnFile() : m.prereadOnFile()
											)}
											{#if unpaired.length}
												<ul
													class="flex flex-col divide-y divide-surface-200-800 border border-surface-200-800 rounded-base bg-surface-50-950"
												>
													{#each unpaired as e (e.id)}
														{@const via = e.via_controls.map(
															(id) =>
																selected.applied_controls.find((c) => c.id === id)?.name ??
																m.prereadControlHiddenLower()
														)}
														{@const stale = e.stale}
														<li class="flex flex-col gap-0.5 p-2.5 text-sm">
															<span class="flex items-baseline gap-2">
																{#if e.name}
																	<a class="anchor grow" href="/evidences/{e.id}">{e.name}</a>
																{:else}
																	<span class="italic text-surface-600-400 grow"
																		>{m.prereadEvidenceHidden()}</span
																	>
																{/if}
																<span
																	hidden={!e.name}
																	class="shrink-0 text-xs tabular-nums {stale || !e.updated_at
																		? 'text-warning-700-300'
																		: 'text-surface-600-400'}"
																	title={stale ? m.prereadOlderThanWindow() : ''}
																>
																	{#if stale || !e.updated_at}<i
																			class="fa-solid fa-clock-rotate-left mr-1"
																		></i>{/if}{ageLabel(e.updated_at)}
																</span>
															</span>
															<span class="text-xs text-surface-600-400 flex flex-wrap gap-x-2">
																{#if e.direct}<span
																		><i class="fa-solid fa-link mr-1"
																		></i>{m.prereadAttachedToRequirement()}</span
																	>{/if}
																{#each via as name, i (i)}
																	<span
																		><i class="fa-solid fa-shield-halved mr-1"></i>{m.prereadVia({
																			name
																		})}</span
																	>
																{/each}
																{#each e.via_tasks ?? [] as name, i (i)}
																	<span
																		><i class="fa-solid fa-list-check mr-1"></i>{m.prereadViaTask({
																			name: name ?? m.prereadTaskHiddenLower()
																		})}</span
																	>
																{/each}
																{#if e.issue && e.has_file}<span class={ISSUE[e.issue]}
																		>{e.name
																			? safeTranslate(e.status)
																			: HIDDEN_ISSUE[e.issue]?.()}{#if e.expiry_date}
																			· {expiryLabel(e)}{/if}</span
																	>{/if}
																{#if !e.has_file && e.name && canAddFile}<button
																		class="anchor text-warning-700-300"
																		onclick={() => addFile(e.id)}
																		><i class="fa-solid fa-file-circle-plus mr-1"
																		></i>{m.prereadNoFile()} · {m.prereadAddFile()}</button
																	>{:else if !e.has_file}<span class="text-warning-700-300"
																		><i class="fa-solid fa-file-circle-exclamation mr-1"
																		></i>{m.prereadNoFile()}</span
																	>{/if}
															</span>
														</li>
													{/each}
												</ul>
											{:else}
												<div
													class="rounded-base border border-dashed border-surface-300-700 bg-surface-50-950 p-4 text-sm text-surface-600-400 flex flex-col gap-1"
												>
													{#if pairedIds.size}
														<span>{m.prereadAllAnswer()}</span>
													{:else}
														<span>{m.prereadNothingLinkedYet()}</span>
														<span>{m.prereadAttachHint()}</span>
													{/if}
												</div>
											{/if}
											{#if selected.applied_controls.length}
												<details class="text-sm mt-1">
													<summary class="cursor-pointer text-surface-600-400">
														{m.prereadAppliedControls({ count: selected.applied_controls.length })}
													</summary>
													<ul class="mt-1 flex flex-col gap-1">
														{#each selected.applied_controls as c (c.id)}
															<li class="flex gap-2 items-baseline">
																{#if c.name}<a class="anchor" href="/applied-controls/{c.id}"
																		>{c.name}</a
																	>{:else}<span class="italic text-surface-600-400"
																		>{m.prereadControlHidden()}</span
																	>{/if}
																<span class="text-xs text-surface-600-400"
																	>{c.status && c.status !== '--'
																		? safeTranslate(c.status)
																		: ''}</span
																>
															</li>
														{/each}
													</ul>
												</details>
											{/if}
										</section>
									</div>
								</section>

								<details id="prep" class="group flex flex-col scroll-mt-4" bind:open={prepOpen}>
									<summary
										class="cursor-pointer list-none flex items-baseline gap-2 text-base font-semibold"
									>
										<i
											class="fa-solid fa-chevron-right text-primary-500 w-4 text-center text-xs transition group-open:rotate-90"
										></i>{m.prereadPrepareInterview()}
										<span class="text-sm font-normal text-surface-500"
											>{m.prereadPrepareInterviewAside()}</span
										>
									</summary>
									<div class="flex flex-col gap-6 mt-4">
										<div class="grid grid-cols-1 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-6">
											<section class="flex flex-col gap-3">
												{@render title('fa-solid fa-comments', m.prereadWillAsk())}
												<ol class="flex flex-col gap-3 border-l-2 border-primary-500/50 pl-4">
													{#each g.questions as q (q.id)}
														<li class="flex gap-3 items-start">
															<span
																class="shrink-0 mt-0.5 rounded px-1.5 text-[11px] font-mono font-semibold leading-5 {q.stage ===
																1
																	? 'border border-surface-300-700 text-surface-600-400'
																	: 'bg-surface-200-800 text-surface-800-200'}"
																title={STAGES[q.stage]}>S{q.stage}</span
															>
															<span class="leading-relaxed text-[15px]">{q.text}</span>
														</li>
													{/each}
												</ol>
											</section>
											<section class="flex flex-col gap-4">
												<div class="flex flex-col gap-2">
													{@render title('fa-solid fa-vials', m.prereadHowChecked())}
													{@render heading('fa-solid fa-layer-group', m.prereadSample())}
													{#if g.sampling.length}
														{@const s = g.sampling[0]}
														<!-- shortcut: rows of one requirement share population and method today; group by them if that changes -->
														<div
															class="rounded-base bg-surface-100-900 p-3 text-sm flex flex-col gap-1"
														>
															<span class="font-semibold"
																>{g.sampling
																	.map(
																		(r) =>
																			`${r.min === r.max ? r.min : `${r.min}–${r.max}`} ${r.unit}`
																	)
																	.join(' + ')}</span
															>
															{#if s.note}<span class="text-surface-600-400">{s.note}</span>{/if}
															{#if s.population}
																<span class="text-surface-600-400"
																	>{m.prereadSampleFrom({ population: s.population })}</span
																>
															{/if}
															{#if s.method}<span class="first-letter:uppercase">{s.method}</span
																>{/if}
														</div>
													{:else}
														<p class="text-sm text-surface-600-400">
															{m.prereadNoSampling()}
														</p>
													{/if}
												</div>
												<div class="flex flex-col gap-2">
													{@render heading('fa-solid fa-user-group', m.prereadInterviews())}
													<div class="flex flex-wrap gap-1.5">
														{#each g.interviewees as w (w)}
															<span
																class="text-xs rounded-full border border-surface-300-700 px-2.5 py-1 flex items-center gap-1.5"
																><i class="fa-solid fa-user text-surface-500 text-[10px]"
																></i>{PEOPLE[w] ?? w}</span
															>
														{/each}
													</div>
												</div>
											</section>
										</div>
										{#if g.pitfalls?.length}
											<section class="flex flex-col gap-3">
												{@render title('fa-solid fa-lightbulb', m.prereadPitfalls())}
												<ul class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
													{#each g.pitfalls as p (p.id)}
														<li
															class="flex gap-2.5 rounded-base border border-surface-200-800 p-3 leading-snug"
														>
															<i
																class="fa-solid fa-magnifying-glass text-primary-500 mt-0.5 text-xs"
															></i>{p.text}
														</li>
													{/each}
												</ul>
											</section>
										{/if}
									</div>
								</details>
							{/if}
						</div>

						<footer
							class="flex items-center justify-between gap-2 px-5 py-3 border-t border-surface-200-800 text-sm"
						>
							<button
								class="btn btn-sm preset-tonal-surface"
								disabled={selectedIndex === 0}
								onclick={() => step(-1)}
							>
								<i class="fa-solid fa-arrow-left"></i>{m.prereadPrevious()}
							</button>
							<span class="text-surface-600-400 tabular-nums"
								>{selectedIndex + 1} / {visible.length}
								<span class="hidden md:inline">{m.prereadKeysHint()}</span></span
							>
							<button
								class="btn btn-sm preset-tonal-surface"
								disabled={selectedIndex >= visible.length - 1}
								onclick={() => step(1)}
							>
								{m.prereadNext()}<i class="fa-solid fa-arrow-right"></i>
							</button>
						</footer>
					</article>
				{/if}
			</div>
		{:else if view === 'sessions'}
			<div class="flex flex-col gap-3">
				<p class="text-sm text-surface-600-400 max-w-3xl">
					{m.prereadSessionsIntro()}
				</p>
				<ol class="flex flex-col gap-3">
					{#each sessions as { session, reqs, people }, n (session.id)}
						{@const planned = prep?.sessions[session.id]}
						{@const byState = SHOWN.map(
							(r) => [r, reqs.filter((x) => x.readiness === r).length] as const
						)}
						{@const asks = reqs.reduce(
							(sum, r) =>
								sum + (r.guidance?.requests.filter((q) => q.kind !== 'observation').length ?? 0),
							0
						)}
						<li class="card border border-surface-200-800 p-4 flex flex-col gap-3">
							<header class="flex flex-wrap items-start gap-x-4 gap-y-2">
								<span
									class="size-7 shrink-0 rounded-full bg-surface-200-800 grid place-items-center text-xs font-semibold tabular-nums"
									>{n + 1}</span
								>
								<div class="flex flex-col grow">
									<h3 class="font-semibold">{session.label}</h3>
									<span class="text-xs text-surface-600-400 tabular-nums"
										>{reqs.length
											? m.prereadSessionCount({ count: reqs.length, asks })
											: m.prereadSessionItems({ count: session.requests?.length ?? 0 })}</span
									>
								</div>
								<span class="flex gap-1.5 text-xs">
									{#each byState as [r, k] (r)}
										{#if k}<span class="flex items-center gap-1 tabular-nums"
												>{@render dot(r)}{k}</span
											>{/if}
									{/each}
								</span>
								{#if toDoIn(session)}
									<button class="btn btn-sm preset-tonal-primary" onclick={() => walk(session.id)}
										><i class="fa-solid fa-shoe-prints"></i>{m.prereadWalk()}</button
									>
								{/if}
							</header>
							<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
								<i class="fa-solid fa-calendar text-surface-500"></i>
								{#if planned?.date}
									<span
										>{new Date(planned.date).toLocaleDateString(getLocale())}{planned.start_time
											? ` · ${planned.start_time.slice(0, 5)}`
											: ''}{planned.end_time
											? `–${planned.end_time.slice(0, 5)}`
											: ''}{planned.location ? ` · ${planned.location}` : ''}</span
									>
									{#if planned.attendees.length}<span class="text-surface-600-400"
											>{planned.attendees.map((a) => a.str).join(', ')}</span
										>{/if}
								{:else}
									<span class="text-surface-600-400">{m.prereadNoDate()}</span>
								{/if}
								{#if canPrepare}
									<button class="anchor text-xs" onclick={() => edit('session', session.id)}
										>{m.prereadSchedule()}</button
									>
								{/if}
							</div>
							{#if editing?.kind === 'session' && editing.key === session.id}
								<div
									class="rounded-base border border-surface-200-800 bg-surface-50-950 p-3 grid gap-3 md:grid-cols-4"
								>
									<label class="flex flex-col gap-1 text-sm"
										><span class="font-medium">{m.date()}</span>
										<input class="input" type="date" bind:value={slot.date} />
									</label>
									<label class="flex flex-col gap-1 text-sm"
										><span class="font-medium">{m.prereadStartTime()}</span>
										<input class="input" type="time" bind:value={slot.start_time} />
									</label>
									<label class="flex flex-col gap-1 text-sm"
										><span class="font-medium">{m.prereadEndTime()}</span>
										<input class="input" type="time" bind:value={slot.end_time} />
									</label>
									<label class="flex flex-col gap-1 text-sm"
										><span class="font-medium">{m.prereadLocation()}</span>
										<input class="input" type="text" bind:value={slot.location} />
									</label>
									<div class="md:col-span-4">
										<AutocompleteSelect
											form={prepForm}
											field="actors"
											multiple
											lazy
											optionsEndpoint="actors"
											optionsLabelField="str"
											label={m.prereadAttendees()}
										/>
									</div>
									<div class="md:col-span-4 flex justify-end gap-2">
										<button class="btn btn-sm preset-tonal-surface" onclick={() => (editing = null)}
											>{m.cancel()}</button
										>
										<button class="btn btn-sm preset-filled-primary-500" onclick={saveEdit}
											>{m.save()}</button
										>
									</div>
								</div>
							{/if}
							{#if people.length}
								<div class="flex flex-wrap gap-1.5">
									{#each people as w (w)}
										<span
											class="text-xs rounded-full border border-surface-300-700 px-2.5 py-1 flex items-center gap-1.5"
											><i class="fa-solid fa-user text-surface-500 text-[10px]"></i>{PEOPLE[w] ??
												w}</span
										>
									{/each}
								</div>
							{/if}
							{#if reqs.length}
								<ul class="text-sm grid grid-cols-1 md:grid-cols-2 gap-x-4 -mx-1">
									{#each reqs as r (r.id)}
										<li>
											<button
												class="w-full flex gap-2 items-center text-left rounded px-1 py-1 hover:bg-surface-100-900"
												onclick={() => openRequirement(r.id)}
											>
												{@render dot(r.readiness)}
												<span class="font-mono text-xs w-14 shrink-0 text-surface-600-400"
													>{r.ref_id}</span
												>
												<span class="leading-snug">{r.name}</span>
											</button>
										</li>
									{/each}
								</ul>
							{/if}
							{#if session.requests?.length}
								<ul class="text-sm flex flex-col gap-1">
									{#each session.requests as q (q.id)}
										<li class="flex gap-2">
											<i class="{KINDS[q.kind]?.icon ?? 'fa-solid fa-file'} mt-1 text-surface-500"
											></i>{q.label}
										</li>
									{/each}
								</ul>
							{/if}
							{#each session.pitfalls ?? [] as p (p.id)}
								<p class="text-sm text-warning-700-300 flex gap-2">
									<i class="fa-solid fa-triangle-exclamation mt-1"></i>{p.text}
								</p>
							{/each}
						</li>
					{/each}
				</ol>
			</div>
		{:else if view === 'requests'}
			<div class="flex flex-col gap-3">
				<div class="flex flex-wrap items-center gap-3">
					<p class="text-sm text-surface-600-400 max-w-3xl">
						{m.prereadRequestsIntro()}
					</p>
					<button class="btn btn-sm preset-filled-primary-500 ml-auto" onclick={copyRequests}>
						<i class="fa-solid {copied ? 'fa-check' : 'fa-copy'}"></i>{copied
							? m.prereadCopied()
							: m.prereadCopyRows({ count: requests.length })}
					</button>
				</div>
				<div class="overflow-auto max-h-[70vh] border border-surface-200-800 rounded-base">
					<table class="table text-sm">
						<thead class="sticky top-0 bg-surface-50-950 z-10">
							<tr>
								<th class="w-8"></th><th>{m.prereadColRef()}</th><th>{m.prereadColRequest()}</th><th
									>{m.prereadColOnFile()}</th
								><th>{m.prereadColKind()}</th><th>{m.prereadColMaxAge()}</th><th
									>{m.prereadColOwner()}</th
								>
							</tr>
						</thead>
						<tbody>
							{#each requests as r, i (i)}
								<tr class="hover:bg-surface-100-900">
									<td>{@render dot(worstOf(r).readiness)}</td>
									<td class="font-mono text-xs">
										<span class="flex flex-wrap gap-x-2 max-w-40">
											{#each r.items as it (it.id)}
												<button
													class="anchor whitespace-nowrap"
													title={it.name}
													onclick={() => openRequirement(it.id)}>{it.ref_id}</button
												>
											{/each}
										</span>
									</td>
									<td class="min-w-64">{r.label}</td>
									<td class="whitespace-nowrap">
										{#if r.filed?.length}
											{@const old = r.filed[0].stale}
											<span
												class="tabular-nums {old ? 'text-warning-700-300' : 'text-success-700-300'}"
												title={r.filed.map((e) => e.name ?? m.prereadEvidenceHidden()).join('\n')}
												><i class="fa-solid {old ? 'fa-clock-rotate-left' : 'fa-check'} mr-1"></i>{r
													.filed.length}</span
											>
										{:else if r.toConfirm}
											<span class="text-primary-700-300" title={m.prereadToConfirmHint()}
												>{m.prereadToConfirm()}</span
											>
										{:else if r.kind === 'observation'}
											<span class="text-surface-500" title={m.prereadSeenOnSite()}>—</span>
										{:else}
											<span class="text-error-600-400">{m.prereadMissing()}</span>
										{/if}
									</td>
									<td class="whitespace-nowrap text-surface-600-400">
										<i class="{KINDS[r.kind]?.icon ?? 'fa-solid fa-file'} mr-1"></i>{KINDS[r.kind]
											?.label ?? r.kind}
									</td>
									<td class="tabular-nums whitespace-nowrap text-surface-600-400"
										>{r.fresh_days ? m.prereadDays({ days: r.fresh_days }) : ''}</td
									>
									<td class="min-w-32"
										>{PEOPLE[r.items[0].guidance?.interviewees[0] ?? ''] ?? ''}</td
									>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
				{#each interviews as [who, reqs] (who)}
					{@const named = prep?.roles[who] ?? []}
					{@const byState = SHOWN.map(
						(r) => [r, reqs.filter((x) => x.readiness === r).length] as const
					)}
					<section class="card border border-surface-200-800 p-4 flex flex-col gap-3">
						<header class="flex items-start justify-between gap-2">
							<div class="flex flex-col">
								<h3 class="font-semibold">{PEOPLE[who] ?? who}</h3>
								<span class="text-xs text-surface-600-400 tabular-nums"
									>{m.prereadWalkThrough({ count: reqs.length })}</span
								>
							</div>
							<span class="flex gap-1.5 text-xs">
								{#each byState as [r, n] (r)}
									{#if n}<span class="flex items-center gap-1 tabular-nums"
											>{@render dot(r)}{n}</span
										>{/if}
								{/each}
							</span>
						</header>
						<div class="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-200-800">
							{#each byState as [r, n] (r)}
								{#if n}<span class={STYLE[r].bar} style="width: {(100 * n) / reqs.length}%"
									></span>{/if}
							{/each}
						</div>
						{#if editing?.kind === 'role' && editing.key === who}
							<div class="flex flex-col gap-2">
								<AutocompleteSelect
									form={prepForm}
									field="actors"
									multiple
									lazy
									optionsEndpoint="actors"
									optionsLabelField="str"
									label={m.prereadWho()}
								/>
								<div class="flex justify-end gap-2">
									<button class="btn btn-sm preset-tonal-surface" onclick={() => (editing = null)}
										>{m.cancel()}</button
									>
									<button class="btn btn-sm preset-filled-primary-500" onclick={saveEdit}
										>{m.save()}</button
									>
								</div>
							</div>
						{:else}
							<p class="text-sm flex flex-wrap items-center gap-x-2">
								<i class="fa-solid fa-user-check text-surface-500"></i>
								<span class={named.length ? '' : 'text-surface-600-400'}
									>{named.map((a) => a.str).join(', ') || m.prereadNobodyYet()}</span
								>
								{#if canPrepare}<button class="anchor text-xs" onclick={() => edit('role', who)}
										>{m.prereadAssign()}</button
									>{/if}
							</p>
						{/if}
						<ul class="text-sm flex flex-col max-h-72 overflow-auto -mx-1">
							{#each reqs as r (r.id)}
								<li>
									<button
										class="w-full flex gap-2 items-center text-left rounded px-1 py-1 hover:bg-surface-100-900"
										onclick={() => openRequirement(r.id)}
									>
										{@render dot(r.readiness)}
										<span class="font-mono text-xs w-14 shrink-0 text-surface-600-400"
											>{r.ref_id}</span
										>
										<span class="leading-snug">{r.name}</span>
									</button>
								</li>
							{/each}
						</ul>
					</section>
				{/each}
			</div>
		{/if}
	{/if}
</div>
