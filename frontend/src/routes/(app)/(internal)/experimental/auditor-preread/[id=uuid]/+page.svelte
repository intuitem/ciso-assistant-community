<script lang="ts">
	import { safeTranslate } from '#lib/utils/i18n.js';
	import type { PageData } from './$types';
	import {
		PEOPLE,
		READINESS,
		REASONS,
		SECTIONS,
		interviewPlan,
		requestList,
		requestListTsv,
		type PrereadItem,
		type Readiness
	} from '../preread';

	let { data }: { data: PageData } = $props();

	const items: PrereadItem[] = $derived(data.preread.items ?? []);
	const TONE: Record<Readiness, string> = {
		gap: 'preset-tonal-error',
		weak: 'preset-tonal-warning',
		ready: 'preset-tonal-success',
		excluded: 'preset-tonal-surface',
		no_guidance: 'preset-tonal-surface'
	};
	const DOT: Record<Readiness, string> = {
		gap: 'bg-error-500',
		weak: 'bg-warning-500',
		ready: 'bg-success-500',
		excluded: 'bg-surface-400',
		no_guidance: 'bg-surface-400'
	};
	const VERDICT: Record<Readiness, string> = {
		gap: 'Likely a nonconformity if the auditor picks this. Prepare before the audit.',
		weak: 'Likely an observation, or a minor nonconformity if it comes up in a sample.',
		ready: 'Nothing to prepare beyond having the linked records open on the day.',
		excluded:
			'Marked not applicable. The auditor will still ask why it is excluded from the Statement of Applicability.',
		no_guidance: 'No auditor guidance for this requirement yet.'
	};

	let view: 'req' | 'requests' | 'interviews' = $state('req');
	let readinessFilter: Readiness | 'all' = $state('all');
	let section = $state('all');
	let stage: 0 | 1 | 2 = $state(0);
	let selectedId: string | undefined = $state();
	let copied = $state(false);

	const counts = $derived(
		Object.fromEntries(
			(Object.keys(READINESS) as Readiness[]).map((r) => [
				r,
				items.filter((i) => i.readiness === r).length
			])
		) as Record<Readiness, number>
	);
	const visible = $derived(
		items.filter(
			(i) =>
				(readinessFilter === 'all' || i.readiness === readinessFilter) &&
				(section === 'all' || SECTIONS.find((s) => s.key === section)!.test(i.urn_suffix)) &&
				(!stage || i.guidance?.questions.some((q) => q.stage === stage))
		)
	);
	const selected = $derived(visible.find((i) => i.id === selectedId) ?? visible[0]);
	const requests = $derived(requestList(visible));
	const interviews = $derived(interviewPlan(visible));

	async function copyRequests() {
		try {
			await navigator.clipboard.writeText(requestListTsv(requests));
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			copied = false;
		}
	}
</script>

{#snippet dot(r: Readiness)}
	<span class="inline-block w-2.5 h-2.5 rounded-sm shrink-0 {DOT[r]}" title={READINESS[r].label}
	></span>
{/snippet}

<div class="p-4 flex flex-col gap-4">
	<div class="flex flex-wrap items-center gap-3">
		<a href="/compliance-assessments/{data.audit.id}" class="anchor font-semibold"
			>{data.audit.name}</a
		>
		<span class="text-surface-600-400 text-sm">{data.audit.framework?.str ?? ''}</span>
		<span class="flex flex-wrap gap-2 ml-auto">
			{#each ['gap', 'weak', 'ready', 'excluded'] as const as r}
				<span class="badge {TONE[r]}">{counts[r]} {READINESS[r].label.toLowerCase()}</span>
			{/each}
		</span>
	</div>

	{#if !data.preread.supported}
		<p class="card preset-tonal-warning p-4">
			There is no auditor guidance for this framework yet. Only ISO/IEC 27001:2022 is covered.
		</p>
	{:else}
		<div class="flex flex-wrap gap-2 items-center text-sm">
			<select class="select w-auto" bind:value={section} aria-label="Section">
				<option value="all">All sections</option>
				{#each SECTIONS as s (s.key)}<option value={s.key}>{s.label}</option>{/each}
			</select>
			<select class="select w-auto" bind:value={stage} aria-label="Audit stage">
				<option value={0}>Stage 1 and 2</option>
				<option value={1}>Stage 1 (documentation)</option>
				<option value={2}>Stage 2 (implementation)</option>
			</select>
			<select class="select w-auto" bind:value={readinessFilter} aria-label="Readiness">
				<option value="all">Any readiness</option>
				{#each ['gap', 'weak', 'ready', 'excluded'] as const as r}
					<option value={r}>{READINESS[r].label}</option>
				{/each}
			</select>
		</div>

		<div class="flex gap-1 border-b border-surface-200-800" role="tablist">
			{#each [['req', 'By requirement'], ['requests', 'Evidence request list'], ['interviews', 'Interview plan']] as [key, label] (key)}
				<button
					role="tab"
					aria-selected={view === key}
					class="px-3 py-2 -mb-px border-b-2 {view === key
						? 'border-primary-500 font-semibold'
						: 'border-transparent text-surface-600-400'}"
					onclick={() => (view = key as typeof view)}>{label}</button
				>
			{/each}
		</div>

		{#if view === 'req'}
			<div class="grid grid-cols-1 lg:grid-cols-[18rem_minmax(0,1fr)] gap-4 items-start">
				<ul class="card border border-surface-200-800 max-h-[70vh] overflow-auto">
					{#each visible as item (item.id)}
						<li>
							<button
								class="w-full grid grid-cols-[4rem_1fr_auto] gap-2 items-center text-left px-3 py-2 border-b border-surface-200-800 {selected?.id ===
								item.id
									? 'bg-primary-500/10'
									: 'hover:bg-surface-100-900'}"
								onclick={() => (selectedId = item.id)}
							>
								<span class="font-mono text-xs text-surface-600-400">{item.ref_id}</span>
								<span class="text-sm">{item.name}</span>
								{@render dot(item.readiness)}
							</button>
						</li>
					{:else}
						<li class="p-3 text-sm text-surface-600-400">Nothing matches these filters.</li>
					{/each}
				</ul>

				{#if selected}
					{@const g = selected.guidance}
					<article class="card border border-surface-200-800 p-5 flex flex-col gap-5 min-w-0">
						<header class="flex flex-wrap items-baseline gap-3">
							<span class="font-mono text-primary-600-400">{selected.ref_id}</span>
							<h2 class="text-lg font-semibold">{selected.name}</h2>
							<a class="anchor text-sm ml-auto" href="/requirement-assessments/{selected.id}"
								>Open requirement</a
							>
						</header>

						<div class="card p-3 {TONE[selected.readiness]}">
							<p class="font-semibold">{READINESS[selected.readiness].label}</p>
							<p class="text-sm">{VERDICT[selected.readiness]}</p>
							{#if selected.reasons.length}
								<ul class="text-sm list-disc pl-5 mt-1">
									{#each selected.reasons as r (r)}<li>{REASONS[r] ?? r}</li>{/each}
									{#each selected.findings as f, i (i)}
										<li>{safeTranslate(f.msgid) === f.msgid ? f.msg : safeTranslate(f.msgid)}</li>
									{/each}
								</ul>
							{/if}
						</div>

						{#if g}
							<div class="grid grid-cols-1 md:grid-cols-2 gap-5">
								<section class="flex flex-col gap-2">
									<h3 class="text-xs uppercase tracking-wider text-surface-600-400 font-semibold">
										What the auditor will ask
									</h3>
									<ol class="list-decimal pl-5 flex flex-col gap-1.5">
										{#each g.questions as q, i (i)}
											<li>
												<span
													class="font-mono text-xs border border-surface-300-700 rounded px-1 mr-1"
													>S{q.stage}</span
												>{q.text}
											</li>
										{/each}
									</ol>
								</section>
								<section class="flex flex-col gap-2">
									<h3 class="text-xs uppercase tracking-wider text-surface-600-400 font-semibold">
										Sample they will pull
									</h3>
									{#if g.sampling}
										<div class="border border-dashed border-surface-300-700 rounded p-3 text-sm">
											<span class="font-mono font-semibold text-primary-600-400"
												>n = {g.sampling.size}</span
											>
											{#if g.sampling.population}<br />From {g.sampling.population}{/if}
											{#if g.sampling.method}<br />{g.sampling.method}{/if}
										</div>
									{:else}
										<p class="text-sm text-surface-600-400">
											Document review, no sampling expected.
										</p>
									{/if}
									<h3
										class="text-xs uppercase tracking-wider text-surface-600-400 font-semibold mt-2"
									>
										Who they will interview
									</h3>
									<div class="flex flex-wrap gap-1.5">
										{#each g.interviewees as w (w)}
											<span class="badge preset-tonal-surface">{PEOPLE[w] ?? w}</span>
										{/each}
									</div>
								</section>
							</div>

							<section class="flex flex-col gap-2">
								<h3 class="text-xs uppercase tracking-wider text-surface-600-400 font-semibold">
									Records they will request
								</h3>
								<div class="overflow-x-auto">
									<table class="table text-sm">
										<thead><tr><th>Request</th><th>Kind</th><th>Max age</th></tr></thead>
										<tbody>
											{#each g.requests as r, i (i)}
												<tr>
													<td>{r.label}</td>
													<td class="font-mono text-xs">{r.kind}</td>
													<td class="font-mono text-xs"
														>{r.fresh_days ? `${r.fresh_days} d` : ''}</td
													>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							</section>
						{/if}

						<section class="grid grid-cols-1 md:grid-cols-2 gap-5">
							<div class="flex flex-col gap-2">
								<h3 class="text-xs uppercase tracking-wider text-surface-600-400 font-semibold">
									Linked evidence ({selected.evidences.length})
								</h3>
								<ul class="text-sm flex flex-col gap-1">
									{#each selected.evidences as e (e.id)}
										{@const via = e.via_controls.map(
											(id) =>
												selected.applied_controls.find((c) => c.id === id)?.name ??
												'a control you cannot view'
										)}
										<li class="flex flex-col">
											<span class="flex gap-2 items-baseline">
												{#if e.name}<a class="anchor" href="/evidences/{e.id}">{e.name}</a
													>{:else}<span class="italic text-surface-600-400"
														>Evidence you cannot view</span
													>{/if}
												<span class="text-xs text-surface-600-400"
													>{e.updated_at
														? `updated ${e.updated_at.slice(0, 10)}`
														: 'no revision'}{e.has_file ? '' : ', no file'}</span
												>
											</span>
											<span class="text-xs text-surface-600-400"
												>{[
													...(e.direct ? ['attached to the requirement'] : []),
													...via.map((name) => `via ${name}`)
												].join(' · ')}</span
											>
										</li>
									{:else}
										<li class="text-surface-600-400">None</li>
									{/each}
								</ul>
							</div>
							<div class="flex flex-col gap-2">
								<h3 class="text-xs uppercase tracking-wider text-surface-600-400 font-semibold">
									Applied controls ({selected.applied_controls.length})
								</h3>
								<ul class="text-sm flex flex-col gap-1">
									{#each selected.applied_controls as c (c.id)}
										<li class="flex gap-2 items-baseline">
											{#if c.name}<a class="anchor" href="/applied-controls/{c.id}">{c.name}</a
												>{:else}<span class="italic text-surface-600-400"
													>Control you cannot view</span
												>{/if}
											<span class="text-xs text-surface-600-400">{safeTranslate(c.status)}</span>
										</li>
									{:else}
										<li class="text-surface-600-400">None</li>
									{/each}
								</ul>
							</div>
						</section>

						{#if g?.pitfalls?.length}
							<section class="flex flex-col gap-2">
								<h3 class="text-xs uppercase tracking-wider text-surface-600-400 font-semibold">
									Where auditors usually find something
								</h3>
								<ul class="list-disc pl-5 text-sm text-surface-700-300">
									{#each g.pitfalls as p, i (i)}<li>{p}</li>{/each}
								</ul>
							</section>
						{/if}
					</article>
				{/if}
			</div>
		{:else if view === 'requests'}
			<div class="flex flex-col gap-3">
				<div class="flex flex-wrap items-center gap-3">
					<p class="text-sm text-surface-600-400 max-w-3xl">
						Every record the auditor is likely to request, worst readiness first. Excluded
						requirements are left out. Paste into a spreadsheet to send ahead of the audit.
					</p>
					<button class="btn btn-sm preset-filled-primary-500 ml-auto" onclick={copyRequests}
						>{copied ? 'Copied' : `Copy ${requests.length} rows`}</button
					>
				</div>
				<div class="overflow-x-auto">
					<table class="table text-sm">
						<thead
							><tr
								><th></th><th>Ref</th><th>Request</th><th>Kind</th><th>Max age</th><th>Owner</th><th
									>Linked</th
								></tr
							></thead
						>
						<tbody>
							{#each requests as r, i (i)}
								<tr>
									<td>{@render dot(r.item.readiness)}</td>
									<td class="font-mono text-xs">{r.item.ref_id}</td>
									<td>{r.label}</td>
									<td class="font-mono text-xs">{r.kind}</td>
									<td class="font-mono text-xs">{r.fresh_days ? `${r.fresh_days} d` : ''}</td>
									<td>{PEOPLE[r.item.guidance?.interviewees[0] ?? ''] ?? ''}</td>
									<td>{r.item.evidences.length}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
				{#each interviews as [who, reqs] (who)}
					{@const gaps = reqs.filter((r) => r.readiness === 'gap').length}
					<div class="card border border-surface-200-800 p-4 flex flex-col gap-2">
						<span class="text-xs font-mono text-primary-600-400"
							>{reqs.length} requirements{gaps ? `, ${gaps} gaps` : ''}</span
						>
						<h3 class="font-semibold">{PEOPLE[who] ?? who}</h3>
						<ul class="text-sm flex flex-col gap-1">
							{#each reqs as r (r.id)}
								<li class="flex gap-2 items-center">
									{@render dot(r.readiness)}<span class="font-mono text-xs w-14 shrink-0"
										>{r.ref_id}</span
									>{r.name}
								</li>
							{/each}
						</ul>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>
