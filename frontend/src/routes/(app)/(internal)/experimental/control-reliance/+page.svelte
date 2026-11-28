<script lang="ts">
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import { m } from '#paraglide/messages.js';
	import type { PageData } from './$types';
	import type { AppliedRow, Counts, Priority, ReferenceRow, ScoredLink } from './reliance';

	let { data }: { data: Pick<PageData, 'portfolio' | 'denied'> } = $props();
	let group = $state<'applied' | 'reference'>('applied');
	let query = $state('');
	let sort = $state<'score' | keyof Counts | 'catalog_requirements'>('score');
	let auditUnit = $state<'requirement_assessments' | 'audits'>('requirement_assessments');
	const pageSize = 20;
	let limit = $state(pageSize);
	const priorities = [1, 2, 3, 4] as const;
	let priorityEdits = $state<
		Record<string, { priority: Priority; saving: boolean; message: string }>
	>({});

	const scored: { key: ScoredLink; label: string; color: string }[] = [
		{ key: 'requirement_assessments', label: 'Requirement assessments', color: 'bg-violet-500' },
		{ key: 'risk_scenarios', label: 'Risk scenarios', color: 'bg-sky-500' },
		{
			key: 'quantitative_risk_existing',
			label: 'Quantitative risk scenarios',
			color: 'bg-teal-500'
		},
		{ key: 'findings', label: 'Findings', color: 'bg-amber-500' },
		{ key: 'open_vulnerabilities', label: 'Open vulnerabilities', color: 'bg-rose-500' },
		{ key: 'data_breaches', label: 'Data-breach remediation', color: 'bg-indigo-500' }
	];
	const context = [
		{ key: 'assets', label: 'Assets' },
		{ key: 'recurring_tasks', label: 'Enabled recurring tasks' },
		{ key: 'threat_models', label: 'Threat models' },
		{ key: 'incidents', label: 'Incidents' },
		{ key: 'resolved_vulnerabilities', label: 'Resolved vulnerabilities' },
		{ key: 'quantitative_risk_added', label: 'Quantitative scenarios considering addition' },
		{ key: 'quantitative_risk_removed', label: 'Quantitative scenarios considering removal' },
		{ key: 'security_exceptions', label: 'Security exceptions' },
		{ key: 'evidences', label: 'Evidence' },
		{ key: 'documents', label: 'Documents' }
	] as const;
	const portfolio = $derived(data.portfolio);
	const source = $derived(
		(group === 'applied' ? portfolio?.applied_controls : portfolio?.reference_controls) ?? []
	);
	const maxScore = $derived(source.reduce((max, row) => Math.max(max, score(row)), 1));

	function count(row: AppliedRow | ReferenceRow, key: ScoredLink) {
		return row.counts[key === 'requirement_assessments' ? auditUnit : key];
	}

	function score(row: AppliedRow | ReferenceRow) {
		return scored.reduce(
			(total, item) => total + count(row, item.key) * (portfolio?.weights[item.key] ?? 0),
			0
		);
	}

	function scoreLabel(item: (typeof scored)[number]) {
		return item.key === 'requirement_assessments' && auditUnit === 'audits'
			? 'Distinct audits'
			: item.label;
	}

	function value(row: AppliedRow | ReferenceRow) {
		if (sort === 'score') return score(row);
		if (sort === 'catalog_requirements')
			return 'catalog_requirements' in row ? row.catalog_requirements : 0;
		return row.counts[sort === 'requirement_assessments' ? auditUnit : sort];
	}

	const matches = $derived.by(() => {
		const needle = query.trim().toLocaleLowerCase();
		return source
			.filter((row) =>
				[row.ref_id, row.name, 'domain' in row ? row.domain : '']
					.join(' ')
					.toLocaleLowerCase()
					.includes(needle)
			)
			.sort(
				(a, b) =>
					value(b) - value(a) ||
					score(b) - score(a) ||
					(a.name || a.ref_id || '').localeCompare(b.name || b.ref_id || '')
			);
	});

	function selectGroup(next: typeof group) {
		group = next;
		sort = 'score';
		query = '';
		limit = pageSize;
	}

	function currentPriority(row: AppliedRow) {
		return row.id in priorityEdits ? priorityEdits[row.id].priority : row.priority;
	}

	async function savePriority(row: AppliedRow, select: HTMLSelectElement) {
		const previous = currentPriority(row);
		const priority = priorities.find((value) => String(value) === select.value) ?? null;
		if (previous === priority) return;
		select.value = String(previous ?? '');
		priorityEdits[row.id] = { priority: previous, saving: true, message: 'Saving…' };
		try {
			const response = await fetch(`/applied-controls/${row.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ priority })
			});
			if (!response.ok) throw new Error('Priority update failed');
			const saved: { priority: Priority } = await response.json();
			priorityEdits[row.id] = { priority: saved.priority, saving: false, message: 'Saved' };
		} catch {
			priorityEdits[row.id] = {
				priority: previous,
				saving: false,
				message: 'Could not save priority'
			};
		}
	}
</script>

<div class="flex flex-col gap-6 p-4 md:p-6">
	<header class="flex flex-col gap-2">
		<Anchor
			href="/experimental"
			class="anchor w-fit text-xs font-semibold tracking-wider uppercase"
		>
			<i class="fa-solid fa-flask mr-1" aria-hidden="true"></i>{m.experimental()}
		</Anchor>
		<h1 class="text-2xl font-semibold">Control reliance</h1>
		<p class="max-w-3xl text-surface-600-400">
			See which controls your audits, risk scenarios, and findings rely on. The score measures
			linked usage, not control effectiveness.
		</p>
	</header>

	{#if !portfolio}
		<p class="card border border-surface-300-700 p-6" role="status">
			{data.denied
				? 'You do not have access to control reliance.'
				: 'Control reliance could not be loaded.'}
		</p>
	{:else}
		<div class="grid grid-cols-3 gap-2 sm:gap-3">
			{#each [['Visible applied controls', portfolio.applied_controls.length], ['With scored links', portfolio.applied_controls.filter((row) => row.score > 0).length], ['Reference controls in view', portfolio.reference_controls.length]] as [label, count] (label)}
				<div class="card border border-surface-200-800 p-3 sm:p-4">
					<div class="text-xs text-surface-600-400 sm:text-sm">{label}</div>
					<div class="text-2xl font-semibold tabular-nums">{count}</div>
				</div>
			{/each}
		</div>

		<section
			class="card flex flex-col gap-4 border border-surface-200-800 p-4"
			aria-label="Control rankings"
		>
			<div class="flex flex-wrap items-end justify-between gap-3">
				<div class="flex flex-wrap gap-1" role="group" aria-label="Group controls by">
					{#each [{ key: 'applied', label: 'Applied controls' }, { key: 'reference', label: 'By reference control' }] as option (option.key)}
						<button
							type="button"
							class="btn btn-sm {group === option.key
								? 'preset-tonal-primary'
								: 'preset-outlined-surface-500'}"
							aria-pressed={group === option.key}
							onclick={() => selectGroup(option.key as typeof group)}>{option.label}</button
						>
					{/each}
				</div>
				<div class="flex max-w-full flex-wrap items-center gap-2">
					<label class="w-full sm:w-60">
						<span class="sr-only">
							{group === 'applied' ? 'Search controls or domains' : 'Search controls'}
						</span>
						<input
							class="input w-full"
							type="search"
							placeholder={group === 'applied' ? 'Search controls or domains' : 'Search controls'}
							bind:value={query}
							oninput={() => (limit = pageSize)}
						/>
					</label>
					<label class="min-w-40">
						<span class="sr-only">Sort by</span>
						<select class="select" bind:value={sort} onchange={() => (limit = pageSize)}>
							<option value="score">Sort: Reliance score</option>
							{#each scored as item (item.key)}
								<option value={item.key}>Sort: {scoreLabel(item)}</option>
							{/each}
							{#each context as item (item.key)}
								<option value={item.key}>Sort: {item.label}</option>
							{/each}
							{#if group === 'reference'}
								<option value="catalog_requirements">Sort: Catalog requirements</option>
							{/if}
						</select>
					</label>
					<label class="min-w-40">
						<span class="sr-only">Count audit links by</span>
						<select class="select" bind:value={auditUnit} onchange={() => (limit = pageSize)}>
							<option value="requirement_assessments">Count: Requirement assessments</option>
							<option value="audits">Count: Distinct audits</option>
						</select>
					</label>
				</div>
			</div>

			<div
				class="flex flex-wrap gap-x-4 gap-y-1 text-sm text-surface-600-400"
				aria-label="Score weights"
			>
				{#each scored as item (item.key)}
					<span class="inline-flex items-center gap-1.5">
						<span class="size-2.5 rounded-full {item.color}" aria-hidden="true"></span>
						{scoreLabel(item)} × {portfolio.weights[item.key]}
					</span>
				{/each}
			</div>

			{#if matches.length === 0}
				<p
					class="rounded border border-dashed border-surface-300-700 p-6 text-center text-surface-600-400"
					role="status"
				>
					{query.trim() ? 'No controls match your search.' : 'No visible controls in this view.'}
				</p>
			{:else}
				<ol class="grid gap-3">
					{#each matches.slice(0, limit) as row, index (row.id)}
						{@const name = row.name || row.ref_id || 'Unnamed control'}
						<li class="rounded-lg border border-surface-200-800 bg-surface-50-950">
							<div
								class="grid gap-4 p-4 sm:grid-cols-[minmax(0,1fr)_minmax(8rem,12rem)_auto] sm:items-start"
							>
								<div class="flex min-w-0 items-start gap-3">
									<span class="w-8 shrink-0 text-right text-xs tabular-nums text-surface-600-400"
										>#{index + 1}</span
									>
									<div class="min-w-0">
										<Anchor
											class="anchor break-words font-semibold"
											href="/{group === 'applied'
												? 'applied-controls'
												: 'reference-controls'}/{row.id}">{name}</Anchor
										>
										<div
											class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-surface-600-400"
										>
											{#if row.ref_id && row.name}<span>{row.ref_id}</span>{/if}
											{#if 'domain' in row}<span
													><i class="fa-solid fa-folder mr-1" aria-hidden="true"
													></i>{row.domain}</span
												>{/if}
											{#if 'implementations' in row}<span
													>{row.implementations} applied {row.implementations === 1
														? 'control'
														: 'controls'}</span
												>{/if}
											{#if row.counts.security_exceptions}
												<span class="badge preset-tonal-warning"
													><i class="fa-solid fa-triangle-exclamation mr-1" aria-hidden="true"
													></i>{row.counts.security_exceptions}
													{row.counts.security_exceptions === 1
														? 'security exception'
														: 'security exceptions'}</span
												>
											{/if}
										</div>
									</div>
								</div>
								<div class="min-w-0 max-w-72">
									<div
										class="flex items-baseline justify-between gap-2 text-xs text-surface-600-400"
									>
										<span>Reliance score</span><strong
											class="text-base tabular-nums text-surface-950-50">{score(row)}</strong
										>
									</div>
									<div
										class="mt-1 flex h-2 overflow-hidden rounded-full bg-surface-200-800"
										aria-hidden="true"
									>
										{#each scored as item (item.key)}
											<span
												class={item.color}
												style:width={`${((count(row, item.key) * portfolio.weights[item.key]) / maxScore) * 100}%`}
											></span>
										{/each}
									</div>
								</div>
								{#if 'domain' in row}
									<div class="min-w-24 text-sm">
										<div class="mb-1 text-xs text-surface-600-400">{m.priority()}</div>
										{#if row.can_edit_priority}
											<select
												class="select w-auto text-sm"
												aria-label={`Priority for ${name}`}
												value={String(currentPriority(row) ?? '')}
												disabled={priorityEdits[row.id]?.saving}
												onchange={(event) => savePriority(row, event.currentTarget)}
											>
												<option value="">{m.notSet()}</option>
												{#each priorities as priority (priority)}<option value={String(priority)}
														>P{priority}</option
													>{/each}
											</select>
											<span class="block text-xs" role="status"
												>{priorityEdits[row.id]?.message ?? ''}</span
											>
										{:else}
											{row.priority == null ? m.notSet() : `P${row.priority}`}
										{/if}
									</div>
								{/if}
							</div>
							<details class="border-t border-surface-200-800 px-4 py-2 text-sm">
								<summary class="cursor-pointer text-surface-700-300"
									>Relationship breakdown <span class="sr-only">for {name}</span></summary
								>
								<div class="mt-3 grid gap-4 md:grid-cols-2">
									<div>
										<h3
											class="mb-2 text-xs font-semibold uppercase tracking-wide text-surface-600-400"
										>
											Scored links
										</h3>
										<dl class="grid gap-1">
											{#each scored as item (item.key)}
												<div class="flex items-start justify-between gap-3">
													<dt>
														{scoreLabel(item)}
														{#if item.key === 'risk_scenarios' && row.counts.risk_scenarios}
															<div class="text-xs text-surface-600-400">
																{row.counts.risk_treatment} treatment · {row.counts.risk_existing} existing
															</div>
														{/if}
													</dt>
													<dd class="shrink-0 tabular-nums">
														{count(row, item.key)} × {portfolio.weights[item.key]}
													</dd>
												</div>
											{/each}
										</dl>
									</div>
									<div>
										<h3
											class="mb-2 text-xs font-semibold uppercase tracking-wide text-surface-600-400"
										>
											Supporting links
										</h3>
										<dl class="grid gap-1">
											{#each context.filter((item) => row.counts[item.key] > 0) as item (item.key)}
												<div class="flex justify-between gap-3">
													<dt>{item.label}</dt>
													<dd class="tabular-nums">{row.counts[item.key]}</dd>
												</div>
											{/each}
											{#if 'catalog_requirements' in row}
												<div class="flex justify-between gap-3">
													<dt>Catalog requirements</dt>
													<dd class="tabular-nums">{row.catalog_requirements}</dd>
												</div>
											{/if}
										</dl>
										{#if !('catalog_requirements' in row) && !context.some((item) => row.counts[item.key] > 0)}
											<p class="text-surface-600-400">No visible supporting links.</p>
										{/if}
									</div>
								</div>
							</details>
						</li>
					{/each}
				</ol>
				<div class="flex flex-wrap items-center justify-between gap-2">
					<span class="text-sm text-surface-600-400" aria-live="polite"
						>Showing {Math.min(limit, matches.length)} of {matches.length}</span
					>
					{#if limit < matches.length}
						<button
							type="button"
							class="btn btn-sm preset-outlined-surface-500"
							onclick={() => (limit += pageSize)}>Show more</button
						>
					{/if}
				</div>
			{/if}
		</section>

		<details class="card border border-surface-200-800 p-4 text-sm">
			<summary class="cursor-pointer font-semibold">How the score works</summary>
			<p class="mt-2 text-surface-600-400">
				Only visible links count. A qualitative risk scenario linked as both treatment and existing
				counts once. An existing control in several quantitative hypotheses counts once per
				scenario; proposed additions and removals are context only. Switch to distinct audits to
				give each audit one contribution regardless of how many requirements rely on the control.
				Reference-control groups count shared objects once. Supporting links and priority changes do
				not affect the score.
			</p>
		</details>
	{/if}
</div>
