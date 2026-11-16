<script lang="ts">
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { tick } from 'svelte';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import type { PageData } from './$types';
	import {
		KINDS,
		PEOPLE,
		READINESS,
		REASONS,
		SECTIONS,
		STAGES,
		interviewPlan,
		isStale,
		requestList,
		requestListTsv,
		sectionOf,
		type PrereadItem,
		type Readiness
	} from '../preread';

	let { data }: { data: PageData } = $props();

	const items: PrereadItem[] = $derived(data.preread.items ?? []);
	const SHOWN: Readiness[] = ['gap', 'weak', 'ready', 'excluded'];
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
	const VERDICT: Record<Readiness, string> = {
		gap: 'Likely a nonconformity if the auditor picks this one. Prepare it before the audit.',
		weak: 'Likely an observation, or a minor nonconformity if it comes up in a sample.',
		ready: 'Nothing to prepare beyond having the records below open on the day.',
		excluded:
			'Marked not applicable. The auditor will still ask why it is excluded from the Statement of Applicability.',
		no_guidance: 'No auditor guidance for this requirement yet.'
	};

	let view: 'req' | 'requests' | 'interviews' = $state('req');
	let readinessFilter: Readiness | 'all' = $state('all');
	let section = $state('all');
	let stage: 0 | 1 | 2 = $state(0);
	let query = $state('');
	let selectedId: string | null = $state(page.url.searchParams.get('req'));
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
	const matchesQuery = (i: PrereadItem) => {
		const q = query.trim().toLowerCase();
		return !q || i.ref_id.toLowerCase().includes(q) || i.name.toLowerCase().includes(q);
	};
	// Section counts ignore the section filter itself, so each chip says what it would show.
	const beforeSection = $derived(
		items.filter(
			(i) =>
				(readinessFilter === 'all' || i.readiness === readinessFilter) &&
				(!stage || i.guidance?.questions.some((q) => q.stage === stage)) &&
				matchesQuery(i)
		)
	);
	const visible = $derived(
		beforeSection.filter(
			(i) => section === 'all' || SECTIONS.find((s) => s.key === section)!.test(i.urn_suffix)
		)
	);
	const grouped = $derived(
		SECTIONS.map((s) => ({ ...s, items: visible.filter((i) => s.test(i.urn_suffix)) })).filter(
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
	const requests = $derived(requestList(visible));
	const interviews = $derived(interviewPlan(visible));
	const filtered = $derived(
		readinessFilter !== 'all' || section !== 'all' || stage !== 0 || query.trim() !== ''
	);

	async function select(id: string, focus = false) {
		selectedId = id;
		const url = new URL(page.url);
		url.searchParams.set('req', id);
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

	function clearFilters() {
		readinessFilter = 'all';
		section = 'all';
		stage = 0;
		query = '';
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

	const pct = (n: number) => (items.length ? (100 * n) / items.length : 0);
	const ageLabel = (iso: string | null) => (iso ? iso.slice(0, 10) : 'no revision');
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
		aria-label="Readiness summary"
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
						>Auditor pre-read</span
					>
					<span class="text-sm text-surface-600-400">{data.audit.framework?.str ?? ''}</span>
				</div>
				<a
					href="/compliance-assessments/{data.audit.id}"
					class="btn btn-sm preset-tonal-surface ml-auto"
				>
					<i class="fa-solid fa-arrow-up-right-from-square"></i>Open the audit
				</a>
			</div>

			{#if data.preread.supported && items.length}
				<div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
					{#each SHOWN as r (r)}
						<button
							class="group text-left rounded-base px-3 pt-2 pb-2.5 border-b-[3px] transition {readinessFilter ===
							r
								? `bg-surface-100-900 ${STYLE[r].border}`
								: 'border-transparent hover:bg-surface-100-900'}"
							aria-pressed={readinessFilter === r}
							title={readinessFilter === r
								? 'Show all'
								: `Show ${READINESS[r].label.toLowerCase()} only`}
							onclick={() => (readinessFilter = readinessFilter === r ? 'all' : r)}
						>
							<span class="block text-3xl font-semibold tabular-nums leading-none">{counts[r]}</span
							>
							<span class="flex items-center gap-1.5 mt-1.5 text-sm text-surface-600-400">
								{@render dot(r)}{READINESS[r].label}
							</span>
						</button>
					{/each}
				</div>
				<div class="flex flex-col gap-1.5">
					<div
						class="flex h-1.5 w-full gap-0.5 overflow-hidden rounded-full"
						role="img"
						aria-label={SHOWN.map((r) => `${counts[r]} ${READINESS[r].label}`).join(', ')}
					>
						{#each SHOWN as r (r)}
							{#if counts[r]}
								<span class={STYLE[r].bar} style="width: {pct(counts[r])}%"></span>
							{/if}
						{/each}
					</div>
					<span class="text-xs text-surface-500">
						{items.length} requirements. Readiness is an estimate from the evidence linked to the audit
						and its quality checks.
					</span>
				</div>
			{/if}
		</div>
	</header>

	{#if !data.preread.supported}
		<p class="card preset-tonal-warning p-4">
			There is no auditor guidance for this framework yet. Only ISO/IEC 27001:2022 is covered.
		</p>
	{:else}
		<!-- Toolbar -->
		<div class="flex flex-col gap-3">
			<div class="flex flex-wrap items-center gap-2">
				<label class="relative grow max-w-sm">
					<span class="sr-only">Search requirements</span>
					<i
						class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-surface-500 text-sm"
					></i>
					<input
						class="input pl-9 w-full"
						type="search"
						placeholder="Search by ref or title"
						bind:value={query}
					/>
				</label>
				<div
					class="flex rounded-base border border-surface-200-800 overflow-hidden text-sm"
					role="group"
					aria-label="Audit stage"
				>
					{#each [[0, 'Both stages'], [1, 'Stage 1'], [2, 'Stage 2']] as [value, label] (value)}
						<button
							class="px-3 py-1.5 {stage === value
								? 'preset-filled-primary-500'
								: 'hover:bg-surface-100-900'}"
							aria-pressed={stage === value}
							title={value ? STAGES[value as number] : 'Questions from both stages'}
							onclick={() => (stage = value as 0 | 1 | 2)}>{label}</button
						>
					{/each}
				</div>
				{#if filtered}
					<button class="btn btn-sm preset-tonal-surface" onclick={clearFilters}>
						<i class="fa-solid fa-xmark"></i>Clear filters
					</button>
				{/if}
			</div>
			<div class="flex flex-wrap gap-1.5 text-sm" role="group" aria-label="Section">
				{#each [{ key: 'all', label: 'All sections', test: () => true }, ...SECTIONS] as s (s.key)}
					{@const n = beforeSection.filter((i) => s.test(i.urn_suffix)).length}
					<button
						class="rounded-full px-3 py-1 border {section === s.key
							? 'preset-filled-primary-500 border-transparent'
							: 'border-surface-200-800 hover:bg-surface-100-900'}"
						aria-pressed={section === s.key}
						onclick={() => (section = s.key)}
					>
						{s.label} <span class="tabular-nums opacity-70">{n}</span>
					</button>
				{/each}
			</div>
		</div>

		<!-- Tabs -->
		<div class="flex gap-1 border-b border-surface-200-800" role="tablist">
			{#each [['req', 'By requirement', 'fa-solid fa-list-check', visible.length], ['requests', 'Evidence request list', 'fa-solid fa-folder-open', requests.length], ['interviews', 'Interview plan', 'fa-solid fa-people-group', interviews.length]] as const as [key, label, icon, n] (key)}
				<button
					role="tab"
					aria-selected={view === key}
					class="flex items-center gap-2 px-3 py-2 -mb-px border-b-2 {view === key
						? 'border-primary-500 font-semibold'
						: 'border-transparent text-surface-600-400 hover:text-surface-950-50'}"
					onclick={() => (view = key)}
				>
					<i class={icon}></i>{label}
					<span class="badge preset-tonal-surface text-xs tabular-nums">{n}</span>
				</button>
			{/each}
		</div>

		{#if view === 'req'}
			<div class="grid grid-cols-1 lg:grid-cols-[20rem_minmax(0,1fr)] gap-5 items-start">
				<!-- Requirement index -->
				<nav
					bind:this={listEl}
					class="card border border-surface-200-800 lg:sticky lg:top-4 max-h-[75vh] overflow-auto"
					aria-label="Requirements"
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
										<span class="leading-snug">{item.name}</span>
										{@render dot(item.readiness)}
									</button>
								</li>
							{/each}
						</ul>
					{:else}
						<div class="p-6 text-center text-sm text-surface-600-400 flex flex-col gap-2">
							<i class="fa-solid fa-filter-circle-xmark text-2xl"></i>
							Nothing matches these filters.
							<button class="anchor" onclick={clearFilters}>Clear filters</button>
						</div>
					{/each}
				</nav>

				<!-- Requirement file -->
				{#if selected}
					{@const g = selected.guidance}
					{@const s = STYLE[selected.readiness]}
					<article class="card border border-surface-200-800 flex flex-col min-w-0">
						<header
							class="flex flex-wrap items-start gap-x-3 gap-y-2 p-5 border-b border-surface-200-800"
						>
							<div class="flex flex-col gap-1 min-w-0 grow">
								<span class="text-xs text-surface-600-400"
									>{sectionOf(selected.urn_suffix).label}</span
								>
								<h2 class="text-xl font-semibold leading-tight">
									<span class="font-mono text-primary-600-400 mr-2">{selected.ref_id}</span
									>{selected.name}
								</h2>
							</div>
							<div class="flex items-center gap-2">
								<span class="badge preset-tonal-surface" title="Result recorded in the audit">
									{safeTranslate(selected.result)}
								</span>
								<a
									class="btn btn-sm preset-tonal-primary"
									href="/requirement-assessments/{selected.id}"
									title="Open this requirement in the audit"
								>
									<i class="fa-solid fa-arrow-up-right-from-square"></i>Open in audit
								</a>
							</div>
						</header>

						<div class="p-5 flex flex-col gap-6">
							<!-- Verdict -->
							<div class="rounded-base bg-surface-100-900 border-l-4 p-4 flex gap-3 {s.border}">
								<i class="{s.icon} {s.text} text-xl mt-0.5"></i>
								<div class="flex flex-col gap-2 min-w-0">
									<p>
										<span class="font-semibold {s.text}"
											>{READINESS[selected.readiness].label}.</span
										>
										{VERDICT[selected.readiness]}
									</p>
									{#if selected.reasons.length}
										<div class="flex flex-wrap gap-1.5">
											{#each selected.reasons as r (r)}
												<span
													class="text-xs rounded-full border border-surface-300-700 px-2 py-0.5 text-surface-700-300"
													>{REASONS[r] ?? r}</span
												>
											{/each}
										</div>
									{/if}
									{#if selected.findings.length}
										<details class="text-sm">
											<summary class="cursor-pointer text-surface-600-400">
												{selected.findings.length} audit quality finding{selected.findings.length >
												1
													? 's'
													: ''}
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

							{#if g}
								<div class="grid grid-cols-1 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-6">
									<section class="flex flex-col gap-3">
										{@render title('fa-solid fa-comments', 'What the auditor will ask')}
										<ol class="flex flex-col gap-3 border-l-2 border-primary-500/50 pl-4">
											{#each g.questions as q, i (i)}
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
											{@render title('fa-solid fa-vials', 'How they will check it')}
											{@render heading('fa-solid fa-layer-group', 'Sample')}
											{#if g.sampling}
												<div
													class="rounded-base bg-surface-100-900 p-3 text-sm flex flex-col gap-1"
												>
													<span class="font-semibold">{g.sampling.size}</span>
													{#if g.sampling.population}
														<span class="text-surface-600-400">From {g.sampling.population}</span>
													{/if}
													{#if g.sampling.method}<span class="first-letter:uppercase"
															>{g.sampling.method}</span
														>{/if}
												</div>
											{:else}
												<p class="text-sm text-surface-600-400">
													Document review only, no sampling expected.
												</p>
											{/if}
										</div>
										<div class="flex flex-col gap-2">
											{@render heading('fa-solid fa-user-group', 'Interviews')}
											<div class="flex flex-wrap gap-1.5">
												{#each g.interviewees as w (w)}
													<span
														class="text-xs rounded-full border border-surface-300-700 px-2.5 py-1 flex items-center gap-1.5"
														><i class="fa-solid fa-user text-surface-500 text-[10px]"></i>{PEOPLE[
															w
														] ?? w}</span
													>
												{/each}
											</div>
										</div>
									</section>
								</div>

								<!-- Requested vs on file -->
								<section class="flex flex-col gap-3">
									{@render title(
										'fa-solid fa-scale-balanced',
										'Requested vs. on file',
										`${g.requests.filter((r) => r.kind !== 'observation').length} to file · ${selected.evidences.length} on file`
									)}
									<div
										class="grid grid-cols-1 xl:grid-cols-2 gap-4 rounded-container bg-surface-100-900 p-3"
									>
										<section class="flex flex-col gap-2">
											{@render heading('fa-solid fa-folder-open', 'The auditor will ask for')}
											<ul
												class="flex flex-col divide-y divide-surface-200-800 border border-surface-200-800 rounded-base bg-surface-50-950"
											>
												{#each g.requests as r, i (i)}
													<li class="flex gap-3 p-2.5 text-sm">
														<i
															class="{KINDS[r.kind]?.icon ??
																'fa-solid fa-file'} text-surface-500 mt-0.5 w-4 text-center"
															title={KINDS[r.kind]?.label ?? r.kind}
														></i>
														<span class="grow">{r.label}</span>
														{#if r.fresh_days}
															<span
																class="shrink-0 text-xs text-surface-600-400 tabular-nums"
																title="The most recent one should be younger than this"
																>≤ {r.fresh_days} d</span
															>
														{/if}
													</li>
												{/each}
											</ul>
										</section>
										<section class="flex flex-col gap-2">
											{@render heading('fa-solid fa-paperclip', 'You have on file')}
											{#if selected.evidences.length}
												<ul
													class="flex flex-col divide-y divide-surface-200-800 border border-surface-200-800 rounded-base bg-surface-50-950"
												>
													{#each selected.evidences as e (e.id)}
														{@const via = e.via_controls.map(
															(id) =>
																selected.applied_controls.find((c) => c.id === id)?.name ??
																'a control you cannot view'
														)}
														{@const stale = isStale(e.updated_at, g)}
														<li class="flex flex-col gap-0.5 p-2.5 text-sm">
															<span class="flex items-baseline gap-2">
																{#if e.name}
																	<a class="anchor grow" href="/evidences/{e.id}">{e.name}</a>
																{:else}
																	<span class="italic text-surface-600-400 grow"
																		>Evidence you cannot view</span
																	>
																{/if}
																<span
																	class="shrink-0 text-xs tabular-nums {stale || !e.updated_at
																		? 'text-warning-700-300'
																		: 'text-surface-600-400'}"
																	title={stale ? 'Older than the freshness window requested' : ''}
																>
																	{#if stale || !e.updated_at}<i
																			class="fa-solid fa-clock-rotate-left mr-1"
																		></i>{/if}{ageLabel(e.updated_at)}
																</span>
															</span>
															<span class="text-xs text-surface-600-400 flex flex-wrap gap-x-2">
																{#if e.direct}<span
																		><i class="fa-solid fa-link mr-1"></i>attached to the
																		requirement</span
																	>{/if}
																{#each via as name, i (i)}
																	<span
																		><i class="fa-solid fa-shield-halved mr-1"></i>via {name}</span
																	>
																{/each}
																{#if !e.has_file}<span class="text-warning-700-300"
																		><i class="fa-solid fa-file-circle-exclamation mr-1"></i>no file
																		or link</span
																	>{/if}
															</span>
														</li>
													{/each}
												</ul>
											{:else}
												<div
													class="rounded-base border border-dashed border-surface-300-700 bg-surface-50-950 p-4 text-sm text-surface-600-400 flex flex-col gap-1"
												>
													<span>Nothing linked yet.</span>
													<span
														>Attach evidence to the applied controls of this requirement, or to the
														requirement itself.</span
													>
												</div>
											{/if}
											{#if selected.applied_controls.length}
												<details class="text-sm mt-1">
													<summary class="cursor-pointer text-surface-600-400">
														{selected.applied_controls.length} applied control{selected
															.applied_controls.length > 1
															? 's'
															: ''}
													</summary>
													<ul class="mt-1 flex flex-col gap-1">
														{#each selected.applied_controls as c (c.id)}
															<li class="flex gap-2 items-baseline">
																{#if c.name}<a class="anchor" href="/applied-controls/{c.id}"
																		>{c.name}</a
																	>{:else}<span class="italic text-surface-600-400"
																		>Control you cannot view</span
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

								{#if g.pitfalls?.length}
									<section class="flex flex-col gap-3">
										{@render title(
											'fa-solid fa-lightbulb',
											'Where auditors usually find something'
										)}
										<ul class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
											{#each g.pitfalls as p, i (i)}
												<li
													class="flex gap-2.5 rounded-base border border-surface-200-800 p-3 leading-snug"
												>
													<i class="fa-solid fa-magnifying-glass text-primary-500 mt-0.5 text-xs"
													></i>{p}
												</li>
											{/each}
										</ul>
									</section>
								{/if}
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
								<i class="fa-solid fa-arrow-left"></i>Previous
							</button>
							<span class="text-surface-600-400 tabular-nums"
								>{selectedIndex + 1} / {visible.length}
								<span class="hidden md:inline">· use ↑ ↓ in the list</span></span
							>
							<button
								class="btn btn-sm preset-tonal-surface"
								disabled={selectedIndex >= visible.length - 1}
								onclick={() => step(1)}
							>
								Next<i class="fa-solid fa-arrow-right"></i>
							</button>
						</footer>
					</article>
				{/if}
			</div>
		{:else if view === 'requests'}
			<div class="flex flex-col gap-3">
				<div class="flex flex-wrap items-center gap-3">
					<p class="text-sm text-surface-600-400 max-w-3xl">
						Every record the auditor is likely to ask for, worst readiness first. Excluded
						requirements are left out. Copy it into a spreadsheet to share with owners ahead of the
						audit.
					</p>
					<button class="btn btn-sm preset-filled-primary-500 ml-auto" onclick={copyRequests}>
						<i class="fa-solid {copied ? 'fa-check' : 'fa-copy'}"></i>{copied
							? 'Copied'
							: `Copy ${requests.length} rows`}
					</button>
				</div>
				<div class="overflow-auto max-h-[70vh] border border-surface-200-800 rounded-base">
					<table class="table text-sm">
						<thead class="sticky top-0 bg-surface-50-950 z-10">
							<tr>
								<th class="w-8"></th><th>Ref</th><th>Request</th><th>Kind</th><th>Max age</th><th
									>Owner</th
								><th class="text-right">On file</th>
							</tr>
						</thead>
						<tbody>
							{#each requests as r, i (i)}
								<tr class="hover:bg-surface-100-900">
									<td>{@render dot(r.item.readiness)}</td>
									<td class="font-mono text-xs whitespace-nowrap">
										<button class="anchor" onclick={() => openRequirement(r.item.id)}
											>{r.item.ref_id}</button
										>
									</td>
									<td>{r.label}</td>
									<td class="whitespace-nowrap text-surface-600-400">
										<i class="{KINDS[r.kind]?.icon ?? 'fa-solid fa-file'} mr-1"></i>{KINDS[r.kind]
											?.label ?? r.kind}
									</td>
									<td class="tabular-nums text-surface-600-400"
										>{r.fresh_days ? `${r.fresh_days} d` : ''}</td
									>
									<td class="whitespace-nowrap"
										>{PEOPLE[r.item.guidance?.interviewees[0] ?? ''] ?? ''}</td
									>
									<td class="text-right tabular-nums">{r.item.evidences.length}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
				{#each interviews as [who, reqs] (who)}
					{@const byState = SHOWN.map(
						(r) => [r, reqs.filter((x) => x.readiness === r).length] as const
					)}
					<section class="card border border-surface-200-800 p-4 flex flex-col gap-3">
						<header class="flex items-start justify-between gap-2">
							<div class="flex flex-col">
								<h3 class="font-semibold">{PEOPLE[who] ?? who}</h3>
								<span class="text-xs text-surface-600-400 tabular-nums"
									>{reqs.length} requirement{reqs.length > 1 ? 's' : ''} to walk through</span
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
