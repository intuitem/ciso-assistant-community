<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import EvidenceViewer from './EvidenceViewer.svelte';
	import ReviewPanel from './ReviewPanel.svelte';
	import {
		PAGE_SIZE,
		SCOPES,
		daysFrom,
		relative,
		type Evidence,
		type RequirementDetail,
		type ReviewStatus,
		type Revision
	} from './types';
	import type { PageData } from './$types';
	import { m } from '#paraglide/messages.js';

	let { data }: { data: PageData } = $props();

	const backLabel = $derived(data.backLabel || (data.audit ? m.audit() : m.evidences()));
	const me = $derived(page.data.user?.id as string | undefined);
	const fourEyes = $derived(!!page.data.settings?.evidence_four_eyes);

	// Seeded from data so SSR renders the queue; the effect below takes over on navigation.
	// svelte-ignore state_referenced_locally
	let rows: Evidence[] = $state(data.evidences as Evidence[]);
	// svelte-ignore state_referenced_locally
	let total = $state(data.count);
	// svelte-ignore state_referenced_locally
	let counts: Record<string, number> = $state({ ...data.counts });
	// svelte-ignore state_referenced_locally
	let selectedId: string | undefined = $state(data.evidences[0]?.id);
	// svelte-ignore state_referenced_locally
	let search = $state(data.search);

	type Decided = Exclude<ReviewStatus, 'pending'>;
	let lastDecision:
		| { ev: Evidence; index: number; removed: boolean; decision: Decided; revisionId: string }
		| undefined = $state();
	let undoTimer: ReturnType<typeof setTimeout>;
	const UNDO_MS = 8000;

	// Reset only when the page data changes (scope, search, filters), not on "load more".
	$effect.pre(() => {
		const d = data;
		untrack(() => {
			rows = d.evidences as Evidence[];
			total = d.count;
			counts = { ...d.counts };
			search = d.search;
			selectedId = rows[0]?.id;
			lastDecision = undefined;
		});
	});

	let revisions: Record<string, Revision[]> = $state({});
	let requirements: Record<string, RequirementDetail[]> = $state({});
	let viewed: Record<string, string> = $state({});
	let reviewedNow = $state(0);
	let busy = $state(false);
	let error = $state('');
	let rejecting = $state(false);
	let loadingMore = $state(false);

	const selected = $derived(rows.find((e) => e.id === selectedId));
	const position = $derived(rows.findIndex((e) => e.id === selectedId));
	const selectedRevisions = $derived(selectedId ? revisions[selectedId] : undefined);
	const viewedRevision = $derived(
		selectedRevisions?.find((r) => r.id === viewed[selectedId ?? '']) ?? selectedRevisions?.[0]
	);

	const inflight = new Set<string>();
	async function loadRevisions(id: string) {
		if (revisions[id] || inflight.has(`rev:${id}`)) return;
		inflight.add(`rev:${id}`);
		const body = await fetch(`/evidence-revisions?evidence=${id}&ordering=-version`)
			.then((r) => r.json())
			.catch(() => ({ results: [] }));
		revisions[id] = (Array.isArray(body) ? body : (body.results ?? [])) as Revision[];
		inflight.delete(`rev:${id}`);
	}
	async function loadRequirements(ev: Evidence) {
		if (requirements[ev.id] || inflight.has(`req:${ev.id}`)) return;
		inflight.add(`req:${ev.id}`);
		const ids = ev.requirement_assessments.map((ra) => ra.id).join(',');
		requirements[ev.id] = ids
			? await fetch(`/evidences/review/requirements?ids=${ids}`)
					.then((r) => (r.ok ? r.json() : []))
					.catch(() => [])
			: [];
	}

	$effect(() => {
		if (!selected) return;
		loadRevisions(selected.id);
		loadRequirements(selected);
		const next = rows[position + 1];
		if (next) loadRevisions(next.id);
	});

	async function loadMore() {
		if (loadingMore || rows.length >= total) return;
		loadingMore = true;
		const body = await fetch(
			`/evidences?${data.listQuery}&limit=${PAGE_SIZE}&offset=${rows.length}`
		)
			.then((r) => r.json())
			.catch(() => ({ results: [] }));
		const known = new Set(rows.map((r) => r.id));
		rows.push(...((body.results ?? []) as Evidence[]).filter((r) => !known.has(r.id)));
		loadingMore = false;
	}

	function select(id: string) {
		selectedId = id;
		error = '';
		rejecting = false;
		document.getElementById(`row-${id}`)?.scrollIntoView({ block: 'nearest' });
	}

	function step(delta: number) {
		if (!rows.length) return;
		const i = Math.min(rows.length - 1, Math.max(0, position + delta));
		select(rows[i].id);
		if (i >= rows.length - 5) loadMore();
	}

	function post(revision: string, decision: ReviewStatus, comment: string) {
		return fetch('/evidences/review/decide', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ revision, decision, comment })
		}).catch(() => undefined);
	}

	function offerUndo(entry: NonNullable<typeof lastDecision>) {
		lastDecision = entry;
		clearTimeout(undoTimer);
		undoTimer = setTimeout(() => (lastDecision = undefined), UNDO_MS);
	}

	async function undo() {
		const u = lastDecision;
		if (!u || busy) return;
		lastDecision = undefined;
		clearTimeout(undoTimer);
		busy = true;
		const res = await post(u.revisionId, 'pending', '');
		busy = false;
		if (!res?.ok) {
			error = m.reviewUndoError();
			return;
		}
		const rev = await res.json();
		if (revisions[u.ev.id]) revisions[u.ev.id] = [rev, ...revisions[u.ev.id].slice(1)];
		if (u.ev.latest_revision) u.ev.latest_revision.review_status = 'pending';
		counts[u.decision] = Math.max(0, (counts[u.decision] ?? 1) - 1);
		counts.pending = (counts.pending ?? 0) + 1;
		reviewedNow = Math.max(0, reviewedNow - 1);
		if (u.removed) {
			rows.splice(Math.min(u.index, rows.length), 0, u.ev);
			total++;
		}
		select(u.ev.id);
	}

	async function decide(decision: Decided, comment: string) {
		const ev = selected;
		const rev = selectedRevisions?.[0];
		if (!ev || !rev || busy) return;
		// A decision always targets the latest file: never send it while an older one is on screen.
		if (viewedRevision && viewedRevision.id !== rev.id) {
			viewed[ev.id] = rev.id;
			error = m.reviewOlderVersionShown();
			return;
		}
		busy = true;
		error = '';
		const res = await post(rev.id, decision, comment);
		busy = false;
		if (!res?.ok) {
			const body = await res?.json().catch(() => ({}));
			if (res?.status === 409) {
				delete revisions[ev.id];
				await loadRevisions(ev.id);
				error = m.reviewStaleVersion();
				return;
			}
			error = body?.decision?.includes?.('four_eyes_uploader_cannot_review')
				? m.reviewFourEyesError()
				: m.reviewSaveError();
			return;
		}
		const before = rev.review_status;
		revisions[ev.id] = [await res.json(), ...revisions[ev.id].slice(1)];
		if (ev.latest_revision) ev.latest_revision.review_status = decision;
		if (before !== decision) {
			counts[before] = Math.max(0, (counts[before] ?? 1) - 1);
			counts[decision] = (counts[decision] ?? 0) + 1;
		}
		if (before === 'pending') reviewedNow++;
		rejecting = false;
		const i = rows.findIndex((r) => r.id === ev.id);
		const removed = data.scope !== 'all' && decision !== data.scope;
		// Undo is for the inbox flow; changing an earlier decision is redone, not undone.
		if (before === 'pending') offerUndo({ ev, index: i, removed, decision, revisionId: rev.id });
		// A filtered tab only lists its own status: the decided row leaves it, which also
		// keeps "load more" offsets aligned with the server's shrunk result set.
		if (removed) {
			rows.splice(i, 1);
			total = Math.max(0, total - 1);
			const next = rows[Math.min(i, rows.length - 1)];
			if (next) select(next.id);
			else selectedId = undefined;
			if (rows.length < total && i >= rows.length - 5) loadMore();
			return;
		}
		const next = rows.slice(i + 1).find((r) => r.latest_revision?.review_status === 'pending');
		if (next) select(next.id);
	}

	let searchTimer: ReturnType<typeof setTimeout>;
	function onSearch() {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			const url = new URL(page.url.href);
			if (search.trim()) url.searchParams.set('search', search.trim());
			else url.searchParams.delete('search');
			goto(url, { reset: false, replaceState: true });
		}, 300);
	}

	function scopeHref(key: string) {
		const url = new URL(page.url.href);
		url.searchParams.set('scope', key);
		return `${url.pathname}${url.search}`;
	}
	const KEEP_ON_CLEAR = ['scope', 'compliance_assessment', 'backUrl', 'backLabel'];
	const clearHref = $derived.by(() => {
		const q = new URLSearchParams();
		for (const [k, v] of page.url.searchParams) if (KEEP_ON_CLEAR.includes(k)) q.append(k, v);
		q.set('scope', data.scope);
		return `?${q}`;
	});

	function onKey(e: KeyboardEvent) {
		const target = e.target as HTMLElement;
		if (target.closest('input, textarea, select, [contenteditable]')) return;
		if ((e.metaKey || e.ctrlKey) && e.key === 'z' && lastDecision) {
			e.preventDefault();
			undo();
			return;
		}
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		const blocked = fourEyes && selectedRevisions?.[0]?.uploaded_by?.id === me;
		switch (e.key) {
			case 'j':
			case 'ArrowDown':
				step(1);
				break;
			case 'k':
			case 'ArrowUp':
				step(-1);
				break;
			case 'a':
				if (!blocked && selectedRevisions?.[0]?.review_status === 'pending') decide('approved', '');
				break;
			case 'r':
				if (!blocked) rejecting = true;
				break;
			case 'Escape':
				rejecting = false;
				break;
			default:
				return;
		}
		e.preventDefault();
	}

	function sentinel(node: HTMLElement) {
		const io = new IntersectionObserver((entries) => {
			if (entries.some((en) => en.isIntersecting)) loadMore();
		});
		io.observe(node);
		return { destroy: () => io.disconnect() };
	}

	const STATUS_LABEL: Record<ReviewStatus, () => string> = {
		pending: m.reviewToReview,
		approved: m.reviewStatusApproved,
		rejected: m.reviewStatusRejected
	};
	const ROW_ICON: Record<ReviewStatus, string> = {
		pending: 'fa-circle-dot text-warning-500',
		approved: 'fa-circle-check text-success-500',
		rejected: 'fa-circle-xmark text-error-500'
	};
</script>

<svelte:window onkeydown={onKey} />

<div class="flex flex-col gap-4 p-4 h-[calc(100vh-11.5rem)] min-h-[36rem]">
	<header class="flex flex-wrap items-center gap-3">
		<a href={data.backUrl} class="btn btn-sm preset-tonal" title={m.back()}
			><i class="fa-solid fa-arrow-left"></i>{backLabel}</a
		>
		<nav class="flex rounded-full bg-surface-100-900 p-1" aria-label={m.reviewScope()}>
			{#each SCOPES as s (s.key)}
				<a
					href={scopeHref(s.key)}
					class="px-3 py-1 rounded-full text-sm flex items-center gap-2 transition-colors {data.scope ===
					s.key
						? 'bg-surface-50-950 shadow-sm font-semibold'
						: 'text-surface-700-300 hover:text-surface-950-50'}"
					aria-current={data.scope === s.key ? 'page' : undefined}
				>
					{s.label()}
					<span
						class="text-xs tabular-nums rounded-full px-1.5 {s.key === 'pending' && counts[s.key]
							? 'bg-warning-500 text-white'
							: 'bg-surface-200-800'}">{counts[s.key] ?? 0}</span
					>
				</a>
			{/each}
		</nav>
		{#if data.audit}
			<a
				href={data.audit.href}
				class="chip preset-tonal-secondary text-xs max-w-48 xl:max-w-64"
				title={m.reviewAuditScope()}
				><i class="fa-solid fa-certificate"></i><span class="truncate">{data.audit.name}</span></a
			>
		{/if}
		{#if data.hasFilters}
			<span class="chip preset-tonal-primary text-xs"
				><i class="fa-solid fa-filter"></i>{m.reviewFiltered()}
				<a href={clearHref} class="ml-1" aria-label={m.reviewClearFilters()}
					><i class="fa-solid fa-xmark"></i></a
				></span
			>
		{/if}
		<span class="grow"></span>
		{#if reviewedNow}
			<span class="text-sm text-surface-600-400"
				><i class="fa-solid fa-check text-success-500 mr-1"></i>{m.reviewReviewedCount({
					count: reviewedNow
				})}</span
			>
		{/if}
	</header>

	{#if rows.length === 0 && !data.search}
		<div class="grow grid place-items-center">
			<div class="text-center space-y-2 text-surface-600-400">
				<i
					class="fa-solid {data.scope === 'pending'
						? 'fa-circle-check text-success-500'
						: 'fa-inbox'} text-4xl"
				></i>
				<p class="text-lg font-semibold text-surface-900-100">
					{data.scope === 'pending' ? m.reviewAllCaughtUp() : m.reviewNothingHere()}
				</p>
				<p class="text-sm">
					{data.scope === 'pending' ? m.reviewNothingWaiting() : m.reviewNoEvidenceMatches()}
				</p>
			</div>
		</div>
	{:else}
		<div class="grid grid-cols-1 lg:grid-cols-[16rem_minmax(0,1fr)_20rem] gap-4 grow min-h-0">
			<aside
				class="card bg-surface-50-950 shadow-sm flex flex-col min-h-0 overflow-hidden"
				aria-label={m.reviewQueue()}
			>
				<div class="p-2 border-b border-surface-200-800 space-y-1">
					<label class="relative block">
						<span class="sr-only">{m.reviewSearchEvidences()}</span>
						<i
							class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-surface-500 text-xs"
						></i>
						<input
							type="search"
							class="input pl-8 w-full text-sm"
							placeholder={m.search()}
							bind:value={search}
							oninput={onSearch}
						/>
					</label>
					<p class="text-xs text-surface-600-400 px-2">
						{total ? m.reviewPosition({ position: position + 1, total }) : m.reviewNoMatch()}
					</p>
				</div>
				<ol class="overflow-auto space-y-0.5 p-2 grow">
					{#each rows as ev (ev.id)}
						{@const rev = ev.latest_revision}
						{@const exp = ev.expiry_date ? daysFrom(ev.expiry_date) : null}
						<li id="row-{ev.id}">
							<button
								class="w-full text-left rounded-xl px-3 py-2 flex gap-3 items-start transition-colors {ev.id ===
								selectedId
									? 'bg-primary-100-900 ring-1 ring-primary-500'
									: 'hover:bg-surface-100-900'}"
								onclick={() => select(ev.id)}
							>
								<i
									class="fa-solid fa-fw shrink-0 {ROW_ICON[rev?.review_status ?? 'pending']} mt-1"
									aria-label={rev ? STATUS_LABEL[rev.review_status]() : undefined}
								></i>
								<span class="min-w-0 grow">
									<span class="block font-medium text-sm truncate">{ev.name}</span>
									<span class="block text-xs text-surface-600-400 truncate">
										{ev.folder?.str}{rev ? ` · v${rev.version} · ${relative(rev.created_at)}` : ''}
									</span>
								</span>
								{#if exp !== null && exp < 30}
									<span
										class="text-[10px] font-semibold shrink-0 mt-1 {exp < 0
											? 'text-error-600-400'
											: 'text-warning-700-300'}"
										title={exp < 0 ? m.expired() : m.reviewExpiresSoon()}
										><i class="fa-regular fa-hourglass-half"></i>{exp < 0
											? m.reviewExpiredShort()
											: m.reviewDaysShort({ days: exp })}</span
									>
								{/if}
							</button>
						</li>
					{/each}
					{#if rows.length < total}
						<li use:sentinel class="py-3 text-center text-xs text-surface-600-400">
							<i class="fa-solid fa-spinner fa-spin mr-1"></i>{m.reviewLoadingMore()}
						</li>
					{/if}
				</ol>
			</aside>

			<main class="card bg-surface-50-950 shadow-sm flex flex-col min-h-0 gap-3 p-4">
				{#if selected}
					<div class="flex items-center gap-2 min-w-0">
						<div class="min-w-0 grow">
							<h1 class="text-lg font-semibold truncate">{selected.name}</h1>
							<p class="text-xs text-surface-600-400 truncate">
								{viewedRevision?.attachment ?? viewedRevision?.link ?? ''}
								{#if viewedRevision?.size}· {viewedRevision.size}{/if}
								{#if viewedRevision && viewedRevision.id !== selectedRevisions?.[0]?.id}
									· <span class="text-warning-700-300 font-semibold"
										>{m.reviewViewingVersion({ version: viewedRevision.version })}</span
									>
									<button class="anchor" onclick={() => selectedId && delete viewed[selectedId]}
										>{m.reviewBackToLatest()}</button
									>
								{/if}
							</p>
						</div>
						{#if viewedRevision?.attachment}
							<a
								class="btn-icon preset-tonal"
								href="/evidence-revisions/{viewedRevision.id}/attachment"
								aria-label={m.download()}
								title={m.download()}><i class="fa-solid fa-download"></i></a
							>
						{/if}
						<a
							class="btn-icon preset-tonal"
							href="/evidences/{selected.id}"
							aria-label={m.reviewOpenEvidence()}
							title={m.reviewOpenEvidence()}
							><i class="fa-solid fa-arrow-up-right-from-square"></i></a
						>
					</div>
					<div class="grow min-h-0">
						<EvidenceViewer revision={viewedRevision} loading={!selectedRevisions} />
					</div>
				{/if}
			</main>

			<div class="card bg-surface-50-950 shadow-sm overflow-auto min-h-0 flex flex-col">
				{#if selected}
					<ReviewPanel
						evidence={selected}
						revisions={selectedRevisions}
						requirements={requirements[selected.id]}
						viewedId={viewedRevision?.id}
						{me}
						{fourEyes}
						{busy}
						{error}
						bind:rejecting
						onView={(id) => selectedId && (viewed[selectedId] = id)}
						onDecide={decide}
					/>
				{/if}
				<p class="text-[11px] text-surface-500 mt-auto px-4 pb-4 pt-2">
					<kbd class="kbd">J</kbd>/<kbd class="kbd">K</kbd>
					{m.reviewKeyMove()} · <kbd class="kbd">A</kbd>
					{m.approve()} · <kbd class="kbd">R</kbd>
					{m.reject()}
				</p>
			</div>
		</div>
	{/if}
	{#if lastDecision}
		<div
			class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 card preset-filled-surface-900-100 shadow-xl flex items-center gap-4 pl-4 pr-2 py-2 text-sm max-w-[90vw]"
			role="status"
			aria-live="polite"
		>
			<i
				class="fa-solid {lastDecision.decision === 'approved'
					? 'fa-circle-check text-success-400 dark:text-success-600'
					: 'fa-circle-xmark text-error-400 dark:text-error-600'}"
			></i>
			<span class="truncate">
				{lastDecision.decision === 'approved'
					? m.reviewToastApproved({ name: lastDecision.ev.name })
					: m.reviewToastRejected({ name: lastDecision.ev.name })}
			</span>
			<button
				class="btn btn-sm shrink-0 font-semibold text-primary-300 dark:text-primary-700 hover:bg-surface-50/10 dark:hover:bg-surface-950/10"
				onclick={undo}
				disabled={busy}>{m.undo()}<kbd class="kbd text-[10px]">⌘Z</kbd></button
			>
		</div>
	{/if}
</div>
