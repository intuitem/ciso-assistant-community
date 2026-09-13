<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { deserialize } from '$app/forms';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	type Outcome = { ref_id: string; label: string; color?: string; description?: string };
	type Row = {
		id: string;
		ref: string;
		name: string;
		form: string;
		formId: string;
		domain: string;
		status: string;
		score: number | null;
		outcomes: Outcome[];
		respondent: string;
		reviewer: string;
		assignee: { id: string; str: string } | null;
		resolution: string;
		created: Date;
		due: Date | null;
		progress: { answered_count: number; total_count: number };
	};

	const COLORS: Record<string, string> = {
		red: 'bg-red-100 text-red-800 ring-red-300 dark:bg-red-950 dark:text-red-200 dark:ring-red-800',
		orange:
			'bg-amber-100 text-amber-900 ring-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:ring-amber-800',
		green:
			'bg-emerald-100 text-emerald-800 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:ring-emerald-800',
		purple:
			'bg-violet-100 text-violet-800 ring-violet-300 dark:bg-violet-950 dark:text-violet-200 dark:ring-violet-800',
		blue: 'bg-sky-100 text-sky-800 ring-sky-300 dark:bg-sky-950 dark:text-sky-200 dark:ring-sky-800'
	};
	const NEUTRAL =
		'bg-surface-100 text-surface-700 ring-surface-300 dark:bg-surface-900 dark:text-surface-300 dark:ring-surface-700';
	const chip = (o: Outcome) => COLORS[o.color ?? ''] ?? NEUTRAL;

	const STATUS_META: Record<string, { label: string; dot: string; order: number }> = {
		draft: { label: m.quickFormDraftStatus(), dot: 'bg-sky-500', order: 0 },
		submitted: { label: m.quickFormQueueOpen(), dot: 'bg-amber-500', order: 1 },
		in_review: { label: m.quickFormQueueInProgress(), dot: 'bg-violet-500', order: 2 },
		closed: { label: m.quickFormQueueDone(), dot: 'bg-surface-400', order: 3 }
	};

	const RESOLUTION: Record<string, string> = {
		accepted: m.quickFormAccepted(),
		rejected: m.quickFormRejected(),
		dropped: m.quickFormDropped(),
		auto: m.quickFormAutoClosed()
	};

	const FORM_ICONS: Record<string, string> = {
		'Derogation request': 'fa-unlock-keyhole',
		'Project framing': 'fa-diagram-project',
		'Entity qualification': 'fa-building-shield',
		'Pre-DPIA screening': 'fa-user-shield'
	};

	const rows: Row[] = $derived(
		(data.responses ?? []).map((r: any) => ({
			id: r.id,
			ref: r.ref_id ?? '',
			name: r.name,
			form: r.quick_form?.name ?? '—',
			formId: r.quick_form?.id ?? '',
			domain: r.folder?.str ?? r.folder?.name ?? '—',
			status: r.status,
			score: r.score,
			outcomes: Object.entries(r.computed_outcome ?? {}).map(([ref_id, v]: [string, any]) => ({
				ref_id,
				label: v?.label ?? ref_id,
				color: v?.color,
				description: v?.description
			})),
			respondent: (r.respondents ?? [])[0]?.str ?? '—',
			reviewer: (r.reviewers ?? [])[0]?.str ?? '—',
			assignee: r.assignee ?? null,
			resolution: r.resolution ?? '',
			created: new Date(r.created_at),
			due: r.due_date ? new Date(r.due_date) : null,
			progress: r.progress ?? { answered_count: 0, total_count: 0 }
		}))
	);

	let view = $state<'triage' | 'board' | 'outcome' | 'table'>('triage');
	let formFilter = $state<string>('');
	let domainFilter = $state<string>('');
	let hideClosed = $state(true);
	let mineOnly = $state(false);
	let busy = $state('');

	const myActorIds = $derived(
		new Set(
			((page.data?.user?.actors ?? []) as { id: string }[])
				.map((a) => a.id)
				.concat(page.data?.user?.actor_id ? [page.data.user.actor_id] : [])
		)
	);
	const isMine = (r: Row) => !!r.assignee && myActorIds.has(r.assignee.id);

	async function transition(id: string, status: string, resolution?: string) {
		if (busy) return;
		busy = id;
		try {
			const body = new FormData();
			body.append('id', id);
			body.append('status', status);
			if (resolution) body.append('resolution', resolution);
			await fetch('?/setStatus', { method: 'POST', body }).then(async (r) =>
				deserialize(await r.text())
			);
			await invalidateAll();
		} finally {
			busy = '';
		}
	}

	const forms = $derived([...new Set(rows.map((r) => r.form))].sort());
	const domains = $derived([...new Set(rows.map((r) => r.domain))].sort());

	// Drafts never reach the reviewer inbox: a request nobody has submitted is not in
	// anyone's queue, and including them is noise. Submitted and up only.
	const visible = $derived(
		rows
			.filter((r) => r.status !== 'draft')
			.filter((r) => !formFilter || r.form === formFilter)
			.filter((r) => !domainFilter || r.domain === domainFilter)
			.filter((r) => !hideClosed || r.status !== 'closed')
			.filter((r) => !mineOnly || isMine(r))
	);

	const today = new Date();
	const days = (d: Date) => Math.floor((today.getTime() - d.getTime()) / 86400000);
	const overdue = (r: Row) => !!r.due && r.due < today && r.status !== 'closed';

	const stats = $derived({
		awaiting: rows.filter((r) => r.status === 'submitted').length,
		overdue: rows.filter(overdue).length,
		drafting: rows.filter((r) => r.status === 'in_review').length,
		mine: rows.filter((r) => r.status !== 'closed' && isMine(r)).length
	});

	// Triage groups by how long the submission has been sitting, not by form or status:
	// the question a reviewer opens this page with is "what is going stale".
	const BUCKETS = [
		{ key: 'overdue', label: 'Overdue or due today', match: (r: Row) => overdue(r) },
		{ key: 'new', label: 'Last 3 days', match: (r: Row) => days(r.created) <= 3 },
		{ key: 'week', label: 'This week', match: (r: Row) => days(r.created) <= 7 },
		{ key: 'older', label: 'Older', match: () => true }
	];

	const bucketed = $derived.by(() => {
		const out: { label: string; rows: Row[] }[] = BUCKETS.map((b) => ({
			label: b.label,
			rows: []
		}));
		for (const r of [...visible].sort((a, b) => b.created.getTime() - a.created.getTime())) {
			const i = BUCKETS.findIndex((b) => b.match(r));
			out[i === -1 ? BUCKETS.length - 1 : i].rows.push(r);
		}
		return out.filter((g) => g.rows.length);
	});

	const columns = $derived(
		['submitted', 'in_review', 'closed'].map((s) => ({
			status: s,
			meta: STATUS_META[s],
			rows: visible.filter((r) => r.status === s)
		}))
	);

	// The decision lens: one submission appears under every outcome it fired, so the
	// page answers "what are these submissions telling us" rather than "who owes what".
	const byOutcome = $derived.by(() => {
		const groups: Record<string, { outcome: Outcome; rows: Row[] }> = {};
		for (const r of visible)
			for (const o of r.outcomes) {
				if (!groups[o.ref_id]) groups[o.ref_id] = { outcome: o, rows: [] };
				groups[o.ref_id].rows.push(r);
			}
		return Object.values(groups).sort((a, b) => b.rows.length - a.rows.length);
	});

	const unresolved = $derived(visible.filter((r) => !r.outcomes.length));

	const fmt = (d: Date | null) =>
		d ? d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '—';
	const href = (r: Row) => `/quick-form-responses/${r.id}`;
</script>

<div class="mb-6 flex flex-wrap items-end justify-between gap-4">
	<div>
		<h1 class="text-2xl font-bold text-surface-900-100">{m.requestQueue()}</h1>
		<p class="text-sm text-surface-500">{m.requestQueueSubtitle()}</p>
	</div>
	<div class="flex gap-2">
		{#each [['triage', 'fa-inbox', m.quickFormViewTriage()], ['board', 'fa-columns', m.quickFormViewBoard()], ['outcome', 'fa-tags', m.quickFormViewOutcome()], ['table', 'fa-table', m.quickFormViewTable()]] as [key, icon, label] (key)}
			<button
				type="button"
				onclick={() => (view = key as typeof view)}
				class="rounded-lg px-3 py-1.5 text-sm font-medium transition-colors {view === key
					? 'bg-violet-600 text-white'
					: 'bg-surface-100-900 text-surface-600-400 hover:bg-surface-200-800'}"
			>
				<i class="fa-solid {icon} mr-1.5"></i>{label}
			</button>
		{/each}
	</div>
</div>

<div class="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
	{#each [[m.quickFormQueueOpen(), stats.awaiting, 'text-amber-600'], [m.overdue(), stats.overdue, 'text-red-600'], [m.quickFormQueueInProgress(), stats.drafting, 'text-violet-600'], [m.quickFormAssignedToMe(), stats.mine, 'text-surface-700-300']] as [label, value, tone] (label)}
		<div class="rounded-xl border border-surface-200-800 bg-surface-50-950 p-4">
			<div class="text-2xl font-bold {tone}">{value}</div>
			<div class="text-xs text-surface-500">{label}</div>
		</div>
	{/each}
</div>

<div class="mb-5 flex flex-wrap items-center gap-2">
	<select bind:value={formFilter} class="select w-auto rounded-lg text-sm">
		<option value="">All forms</option>
		{#each forms as f (f)}<option value={f}>{f}</option>{/each}
	</select>
	<select bind:value={domainFilter} class="select w-auto rounded-lg text-sm">
		<option value="">All domains</option>
		{#each domains as d (d)}<option value={d}>{d}</option>{/each}
	</select>
	<label class="flex items-center gap-2 text-sm text-surface-600-400">
		<input type="checkbox" class="checkbox" bind:checked={mineOnly} />
		{m.quickFormAssignedToMe()}
	</label>
	<label class="flex items-center gap-2 text-sm text-surface-600-400">
		<input type="checkbox" class="checkbox" bind:checked={hideClosed} />
		{m.quickFormHideDone()}
	</label>
	<span class="ml-auto text-sm text-surface-500">{visible.length}</span>
</div>

{#snippet outcomeChips(row: Row)}
	{#if row.outcomes.length}
		<div class="flex flex-wrap gap-1">
			{#each row.outcomes as o (o.ref_id)}
				<span
					class="rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset {chip(o)}"
					title={o.description ?? ''}>{o.label}</span
				>
			{/each}
		</div>
	{:else}
		<span class="text-[11px] italic text-surface-400">no outcome yet</span>
	{/if}
{/snippet}

{#snippet queueActions(row: Row)}
	{#if row.status === 'submitted'}
		<button
			type="button"
			disabled={!!busy}
			onclick={(e) => {
				e.preventDefault();
				transition(row.id, 'in_review');
			}}
			class="rounded-md px-2 py-1 text-[11px] font-medium text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-950"
			title={m.quickFormClaim()}><i class="fa-solid fa-hand"></i></button
		>
	{/if}
	{#if row.status === 'submitted' || row.status === 'in_review'}
		<button
			type="button"
			disabled={!!busy}
			onclick={(e) => {
				e.preventDefault();
				transition(row.id, 'closed', 'accepted');
			}}
			class="rounded-md px-2 py-1 text-[11px] font-medium text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950"
			title={m.quickFormAccept()}><i class="fa-solid fa-check"></i></button
		>
		<button
			type="button"
			disabled={!!busy}
			onclick={(e) => {
				e.preventDefault();
				transition(row.id, 'closed', 'rejected');
			}}
			class="rounded-md px-2 py-1 text-[11px] font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
			title={m.quickFormReject()}><i class="fa-solid fa-xmark"></i></button
		>
	{/if}
{/snippet}

{#snippet formBadge(row: Row)}
	<span
		class="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-surface-100-900 px-2 py-0.5 text-[11px] font-medium text-surface-600-400"
	>
		<i class="fa-solid {FORM_ICONS[row.form] ?? 'fa-clipboard-question'}"></i>{row.form}
	</span>
{/snippet}

{#if view === 'triage'}
	<div class="space-y-6">
		{#each bucketed as group (group.label)}
			<section>
				<h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-surface-500">
					{group.label} <span class="text-surface-400">({group.rows.length})</span>
				</h2>
				<div
					class="divide-y divide-surface-200-800 overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950"
				>
					{#each group.rows as row (row.id)}
						<a
							href={href(row)}
							class="flex items-center gap-4 p-4 transition-colors hover:bg-surface-100-900"
						>
							<span class="h-2 w-2 shrink-0 rounded-full {STATUS_META[row.status]?.dot}"></span>
							<div class="min-w-0 flex-1">
								<div class="flex flex-wrap items-center gap-2">
									{#if row.ref}
										<span class="shrink-0 font-mono text-[11px] text-surface-400">{row.ref}</span>
									{/if}
									<span class="truncate font-semibold text-surface-900-100">{row.name}</span>
									{@render formBadge(row)}
								</div>
								<div class="mt-1.5">{@render outcomeChips(row)}</div>
							</div>
							<div class="hidden shrink-0 text-right text-xs text-surface-500 sm:block">
								<div>{row.respondent}</div>
								<div class="text-surface-400">{row.domain}</div>
							</div>
							<div class="w-24 shrink-0 text-right text-xs">
								{#if row.assignee}
									<span class="text-violet-600" title={m.quickFormAssignedTo()}
										><i class="fa-solid fa-user-check mr-1"></i>{row.assignee.str}</span
									>
								{:else if row.score !== null}
									<span class="font-mono font-semibold text-surface-700-300">{row.score}</span>
								{/if}
								<div class={overdue(row) ? 'font-medium text-red-600' : 'text-surface-400'}>
									{row.resolution ? RESOLUTION[row.resolution] : fmt(row.due)}
								</div>
							</div>
							<div class="flex shrink-0 items-center gap-0.5">{@render queueActions(row)}</div>
						</a>
					{/each}
				</div>
			</section>
		{/each}
	</div>
{:else if view === 'board'}
	<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
		{#each columns as col (col.status)}
			<div class="rounded-xl bg-surface-100-900 p-3">
				<h2
					class="mb-3 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-surface-500"
				>
					<span class="h-2 w-2 rounded-full {col.meta.dot}"></span>
					{col.meta.label}
					<span class="ml-auto text-surface-400">{col.rows.length}</span>
				</h2>
				<div class="space-y-2">
					{#each col.rows as row (row.id)}
						<a
							href={href(row)}
							class="block rounded-lg border border-surface-200-800 bg-surface-50-950 p-3 shadow-sm transition-shadow hover:shadow-md"
						>
							<div class="mb-1.5 flex items-start justify-between gap-2">
								<span class="text-sm font-semibold text-surface-900-100">{row.name}</span>
								{#if row.score !== null}
									<span class="shrink-0 font-mono text-xs text-surface-500">{row.score}</span>
								{/if}
							</div>
							{@render formBadge(row)}
							<div class="mt-2">{@render outcomeChips(row)}</div>
							<div class="mt-2 flex items-center justify-between text-[11px] text-surface-400">
								<span>{row.assignee ? row.assignee.str : row.respondent}</span>
								<span class={overdue(row) ? 'font-medium text-red-600' : ''}
									>{row.resolution ? RESOLUTION[row.resolution] : fmt(row.due)}</span
								>
							</div>
							<div class="mt-1 flex items-center gap-0.5">{@render queueActions(row)}</div>
						</a>
					{/each}
					{#if !col.rows.length}
						<p class="px-1 py-6 text-center text-xs text-surface-400">Nothing here</p>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{:else if view === 'outcome'}
	<div class="space-y-4">
		{#each byOutcome as group (group.outcome.ref_id)}
			<section class="overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950">
				<header class="flex flex-wrap items-center gap-3 border-b border-surface-200-800 p-4">
					<span
						class="rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset {chip(
							group.outcome
						)}">{group.outcome.label}</span
					>
					<span class="text-sm text-surface-500">{group.rows.length} submissions</span>
					{#if group.outcome.description}
						<span class="w-full text-xs text-surface-500 sm:w-auto sm:flex-1">
							{group.outcome.description}
						</span>
					{/if}
				</header>
				<div class="divide-y divide-surface-200-800">
					{#each group.rows as row (row.id)}
						<a
							href={href(row)}
							class="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors hover:bg-surface-100-900"
						>
							<span class="h-1.5 w-1.5 shrink-0 rounded-full {STATUS_META[row.status]?.dot}"></span>
							<span class="flex-1 truncate text-surface-800-200">{row.name}</span>
							{@render formBadge(row)}
							<span class="hidden w-24 shrink-0 text-right text-xs text-surface-400 sm:block"
								>{row.respondent}</span
							>
						</a>
					{/each}
				</div>
			</section>
		{/each}
		{#if unresolved.length}
			<section class="rounded-xl border border-dashed border-surface-300-700 p-4">
				<h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-surface-500">
					No outcome yet <span class="text-surface-400">({unresolved.length})</span>
				</h2>
				<div class="flex flex-wrap gap-2">
					{#each unresolved as row (row.id)}
						<a
							href={href(row)}
							class="rounded-lg bg-surface-100-900 px-2.5 py-1 text-xs text-surface-600-400 hover:bg-surface-200-800"
							>{row.name}</a
						>
					{/each}
				</div>
			</section>
		{/if}
	</div>
{:else}
	<div class="overflow-x-auto rounded-xl border border-surface-200-800">
		<table class="w-full min-w-[900px] text-sm">
			<thead class="bg-surface-100-900 text-left text-xs uppercase tracking-wide text-surface-500">
				<tr>
					<th class="p-3">Ref</th>
					<th class="p-3">Submission</th>
					<th class="p-3">Form</th>
					<th class="p-3">Domain</th>
					<th class="p-3">Status</th>
					<th class="p-3 text-right">Score</th>
					<th class="p-3">Outcomes</th>
					<th class="p-3">Submitter</th>
					<th class="p-3">Due</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-surface-200-800 bg-surface-50-950">
				{#each visible as row (row.id)}
					<tr class="transition-colors hover:bg-surface-100-900">
						<td class="p-3 font-mono text-xs text-surface-400">{row.ref || '—'}</td>
						<td class="p-3 font-medium"
							><a href={href(row)} class="text-violet-600 hover:underline">{row.name}</a></td
						>
						<td class="p-3 text-surface-500">{row.form}</td>
						<td class="p-3 text-surface-500">{row.domain}</td>
						<td class="p-3">
							<span class="inline-flex items-center gap-1.5 text-xs text-surface-600-400">
								<span class="h-1.5 w-1.5 rounded-full {STATUS_META[row.status]?.dot}"></span>
								{STATUS_META[row.status]?.label}
							</span>
						</td>
						<td class="p-3 text-right font-mono text-xs">{row.score ?? '—'}</td>
						<td class="p-3">{@render outcomeChips(row)}</td>
						<td class="p-3 text-xs text-surface-500">{row.respondent}</td>
						<td class="p-3 text-xs {overdue(row) ? 'font-medium text-red-600' : 'text-surface-500'}"
							>{fmt(row.due)}</td
						>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
