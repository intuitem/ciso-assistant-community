<script lang="ts">
	import type { PageData } from './$types';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const r = $derived(data.report);
	const d = $derived(r.description);

	const measureStatusClass: Record<string, string> = {
		implemented: 'preset-tonal-success',
		partially_implemented: 'preset-tonal-warning',
		planned: 'preset-tonal-surface',
		deprecated: 'preset-tonal-error'
	};
</script>

{#snippet empty()}
	<p class="text-sm italic text-surface-500">{m.dpiaNotProvided()}</p>
{/snippet}

{#snippet text(value: string | null | undefined)}
	{#if value}
		<MarkdownRenderer content={value} />
	{:else}
		{@render empty()}
	{/if}
{/snippet}

{#snippet level(risk: { name?: string; hexcolor?: string } | null | undefined)}
	{#if risk && risk.name && risk.name !== '--'}
		<span class="px-2 py-0.5 rounded text-xs font-medium" style="background: {risk.hexcolor}"
			>{risk.name}</span
		>
	{:else}
		<span class="text-surface-400-600">--</span>
	{/if}
{/snippet}

{#snippet register(reg: any)}
	{#if reg}
		<p class="text-sm text-surface-600-400">
			<a class="anchor" href="/risk-assessments/{reg.id}">{reg.name}</a> · {reg.risk_matrix}
		</p>
		{#if reg.scenarios.length}
			<div class="overflow-x-auto">
				<table class="table text-sm">
					<thead>
						<tr>
							<th>{m.refId()}</th>
							<th>{m.name()}</th>
							<th>{m.assets()}</th>
							<th>{m.inherentLevel()}</th>
							<th>{m.currentLevel()}</th>
							<th>{m.residualLevel()}</th>
							<th>{m.appliedControls()}</th>
						</tr>
					</thead>
					<tbody>
						{#each reg.scenarios as s}
							<tr>
								<td class="whitespace-nowrap">{s.ref_id}</td>
								<td><a class="anchor" href="/risk-scenarios/{s.id}">{s.name}</a></td>
								<td>{s.assets.join(', ')}</td>
								<td>{@render level(s.inherent)}</td>
								<td>{@render level(s.current)}</td>
								<td>{@render level(s.residual)}</td>
								<td>{s.applied_controls.join(', ')}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			{@render empty()}
		{/if}
	{:else}
		{@render empty()}
	{/if}
{/snippet}

<article
	class="dpia-report flex flex-col gap-8 max-w-5xl mx-auto bg-surface-50-950 p-8 rounded-lg shadow-sm"
>
	<header class="flex flex-col gap-2 border-b pb-4">
		<div class="flex items-center justify-between gap-4 print:hidden">
			<a class="anchor text-sm" href="/dpias/{data.id}">
				<i class="fa-solid fa-arrow-left mr-1"></i>{m.back()}
			</a>
			<button class="btn preset-tonal btn-sm" onclick={() => window.print()}>
				<i class="fa-solid fa-print mr-2"></i>{m.printReport()}
			</button>
		</div>
		<p class="text-xs uppercase tracking-wider text-surface-500">{m.dpiaReport()}</p>
		<h1 class="text-2xl font-bold">{r.overview.dpia.name}</h1>
		<p class="text-sm text-surface-600-400">
			{r.overview.processing.ref_id}
			{r.overview.processing.name} · {r.overview.folder} · {m.version()}
			{r.overview.dpia.version}
			{#if r.decision.value}
				· <span class="font-semibold">{safeTranslate(r.decision.value)}</span>
			{/if}
		</p>
		{#if r.missing.length}
			<div class="card preset-tonal-warning p-3 text-sm print:hidden">
				<i class="fa-solid fa-triangle-exclamation mr-2"></i>
				{m.dpiaMissingItems({ count: r.missing.length })}
			</div>
		{/if}
	</header>

	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-semibold">§0 {m.dpiaOverview()}</h2>
		<dl class="grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 text-sm">
			<dt class="font-medium">{m.processing()}</dt>
			<dd>
				<a class="anchor" href="/processings/{r.overview.processing.id}"
					>{r.overview.processing.name}</a
				>
			</dd>
			<dt class="font-medium">{m.status()}</dt>
			<dd>{r.overview.processing.status}</dd>
			<dt class="font-medium">{m.nature()}</dt>
			<dd>{r.overview.processing.nature.join(', ') || '--'}</dd>
			<dt class="font-medium">{m.dataContractors()}</dt>
			<dd>
				{d.contractors.map((c: any) => `${c.name} (${c.relationship_type})`).join(', ') || '--'}
			</dd>
		</dl>
		{@render text(r.overview.processing.description)}
	</section>

	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-semibold">§0.5 {m.dpiaTechnicalSheet()}</h2>
		<dl class="grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 text-sm">
			<dt class="font-medium">{m.screening()}</dt>
			<dd>
				{#if r.technical_sheet.screening}
					<a class="anchor" href="/quick-form-responses/{r.technical_sheet.screening.id}"
						>{r.technical_sheet.screening.ref_id}</a
					>
					· {r.technical_sheet.screening.outcomes.map((o: any) => o.label).join(' · ')}
				{:else}
					--
				{/if}
			</dd>
			<dt class="font-medium">{m.reasons()}</dt>
			<dd>{r.technical_sheet.reasons.map((x: any) => x.label).join(' · ') || '--'}</dd>
			<dt class="font-medium">{m.authors()}</dt>
			<dd>{r.technical_sheet.authors.join(', ') || '--'}</dd>
			<dt class="font-medium">{m.reviewers()}</dt>
			<dd>{r.technical_sheet.reviewers.join(', ') || '--'}</dd>
			<dt class="font-medium">{m.validatedBy()}</dt>
			<dd>{r.technical_sheet.validated_by ?? '--'}</dd>
			<dt class="font-medium">{m.validatedAt()}</dt>
			<dd>{r.technical_sheet.validated_at ?? '--'}</dd>
			<dt class="font-medium">{m.reviewDue()}</dt>
			<dd>{r.technical_sheet.review_due ?? '--'}</dd>
		</dl>
		<h3 class="font-medium text-sm">{m.scopeBoundaries()}</h3>
		{@render text(r.technical_sheet.scope_boundaries)}
	</section>

	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-semibold">§1 {m.dpiaSystematicDescription()}</h2>
		<h3 class="font-medium">{m.purposes()}</h3>
		{#if d.purposes.length}
			<table class="table text-sm">
				<thead
					><tr><th>{m.name()}</th><th>{m.legalBasis()}</th><th>{m.article9Condition()}</th></tr
					></thead
				>
				<tbody>
					{#each d.purposes as p}
						<tr
							><td>{p.name}</td><td>{p.legal_basis}</td><td>{p.article_9_condition ?? '--'}</td></tr
						>
					{/each}
				</tbody>
			</table>
		{:else}
			{@render empty()}
		{/if}

		<h3 class="font-medium">{m.personalData()}</h3>
		{#if d.personal_data.length}
			<table class="table text-sm">
				<thead>
					<tr
						><th>{m.name()}</th><th>{m.category()}</th><th>{m.retention()}</th><th
							>{m.deletionPolicy()}</th
						><th>{m.isSensitive()}</th></tr
					>
				</thead>
				<tbody>
					{#each d.personal_data as pd}
						<tr>
							<td>{pd.name}</td>
							<td>{pd.category ? safeTranslate(pd.category) : '--'}</td>
							<td>{pd.retention || '--'}</td>
							<td>{pd.deletion_policy || '--'}</td>
							<td>{pd.is_sensitive ? m.yes() : m.no()}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			{@render empty()}
		{/if}

		<div class="grid md:grid-cols-2 gap-6">
			<div>
				<h3 class="font-medium">{m.dataSubjects()}</h3>
				{#if d.data_subjects.length}
					<ul class="list-disc pl-5 text-sm">
						{#each d.data_subjects as ds}<li>{ds.name} — {ds.category}</li>{/each}
					</ul>
				{:else}
					{@render empty()}
				{/if}
			</div>
			<div>
				<h3 class="font-medium">{m.dataRecipients()}</h3>
				{#if d.recipients.length}
					<ul class="list-disc pl-5 text-sm">
						{#each d.recipients as rc}<li>{rc.name} — {rc.category}</li>{/each}
					</ul>
				{:else}
					{@render empty()}
				{/if}
			</div>
		</div>

		<h3 class="font-medium">{m.dataTransfers()}</h3>
		{#if d.transfers.length}
			<table class="table text-sm">
				<thead
					><tr
						><th>{m.name()}</th><th>{m.entity()}</th><th>{m.country()}</th><th
							>{m.transferMechanism()}</th
						></tr
					></thead
				>
				<tbody>
					{#each d.transfers as t}
						<tr
							><td>{t.name}</td><td>{t.entity ?? '--'}</td><td>{t.country}</td><td
								>{t.transfer_mechanism || '--'}</td
							></tr
						>
					{/each}
				</tbody>
			</table>
		{:else}
			{@render empty()}
		{/if}

		<h3 class="font-medium">{m.supportingAssets()}</h3>
		{#if d.supporting_assets.length}
			<ul class="flex flex-wrap gap-2 text-sm">
				{#each d.supporting_assets as a}
					<li><a class="chip preset-tonal" href="/assets/{a.id}">{a.name}</a></li>
				{/each}
			</ul>
		{:else}
			{@render empty()}
		{/if}
	</section>

	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-semibold">§2 {m.dpiaComplianceMeasures()}</h2>
		{#if r.measures.length}
			<table class="table text-sm">
				<thead
					><tr
						><th>{m.refId()}</th><th>{m.name()}</th><th>{m.owner()}</th><th>{m.eta()}</th><th
							>{m.status()}</th
						></tr
					></thead
				>
				<tbody>
					{#each r.measures as c}
						<tr>
							<td class="whitespace-nowrap">{c.ref_id ?? ''}</td>
							<td><a class="anchor" href="/applied-controls/{c.id}">{c.name}</a></td>
							<td>{c.owner.join(', ') || '--'}</td>
							<td>{c.eta ?? '--'}</td>
							<td
								><span class="badge {measureStatusClass[c.edpb_status]}"
									>{safeTranslate(c.edpb_status)}</span
								></td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			{@render empty()}
		{/if}
	</section>

	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-semibold">§3 {m.dpiaNecessityProportionality()}</h2>
		<h3 class="font-medium">{m.necessity()}</h3>
		{@render text(r.necessity_proportionality.necessity)}
		<h3 class="font-medium">{m.proportionality()}</h3>
		{@render text(r.necessity_proportionality.proportionality)}
		<h3 class="font-medium">{m.designRiskAssessment()}</h3>
		{@render register(r.necessity_proportionality.design_risk)}
	</section>

	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-semibold">§4 {m.incidentRiskAssessment()}</h2>
		<h3 class="font-medium">{m.methodStatement()}</h3>
		{@render text(r.incident_risk.method_statement)}
		{@render register(r.incident_risk.register)}
	</section>

	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-semibold">§5 {m.dpiaOpinions()}</h2>
		<h3 class="font-medium">{m.dpoOpinion()}</h3>
		{@render text(r.opinions.dpo_opinion)}
		<h3 class="font-medium">{m.dpoAdviceApplied()}</h3>
		{@render text(r.opinions.dpo_advice_applied)}
		<h3 class="font-medium">{m.dataSubjectViews()}</h3>
		{#if r.opinions.data_subject_views}
			{@render text(r.opinions.data_subject_views)}
		{:else}
			{@render text(r.opinions.views_not_sought_reason)}
		{/if}
	</section>

	<section class="flex flex-col gap-3">
		<h2 class="text-lg font-semibold">§6 {m.decision()}</h2>
		{#if r.decision.value}
			<p class="font-semibold">{safeTranslate(r.decision.value)}</p>
		{:else}
			{@render empty()}
		{/if}
		<h3 class="font-medium">{m.conditions()}</h3>
		{@render text(r.decision.conditions)}
	</section>
</article>
