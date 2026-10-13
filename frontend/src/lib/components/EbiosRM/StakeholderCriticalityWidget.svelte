<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		stakeholder: Record<string, any>;
	}

	let { stakeholder }: Props = $props();

	// Dependency and penetration raise criticality (numerator); maturity and trust lower it.
	const CRITERIA = [
		{ key: 'dependency', label: m.dependency(), lowerIsBetter: true },
		{ key: 'penetration', label: m.penetration(), lowerIsBetter: true },
		{ key: 'maturity', label: m.maturity(), lowerIsBetter: false },
		{ key: 'trust', label: m.trust(), lowerIsBetter: false }
	] as const;

	type Criterion = (typeof CRITERIA)[number]['key'];

	const entityDefaults = $derived(
		Object.fromEntries(
			CRITERIA.map(({ key }) => [key, stakeholder.entity?.[`default_${key}`] ?? null])
		) as Record<Criterion, number | null>
	);
	const hasEntityDefaults = $derived(
		CRITERIA.every(({ key }) => entityDefaults[key] !== null && entityDefaults[key] !== undefined)
	);

	function criticality(values: Record<Criterion, number | null>): string {
		const { dependency, penetration, maturity, trust } = values;
		if ([dependency, penetration, maturity, trust].some((v) => v === null || v === undefined)) {
			return '--';
		}
		const denominator = (maturity as number) * (trust as number);
		const value =
			denominator === 0 ? 0 : ((dependency as number) * (penetration as number)) / denominator;
		return Number(value.toFixed(2)).toString();
	}

	const current = $derived(
		Object.fromEntries(CRITERIA.map(({ key }) => [key, stakeholder[`current_${key}`]])) as Record<
			Criterion,
			number
		>
	);
	const residual = $derived(
		Object.fromEntries(CRITERIA.map(({ key }) => [key, stakeholder[`residual_${key}`]])) as Record<
			Criterion,
			number
		>
	);

	const isModified = (key: Criterion) => hasEntityDefaults && current[key] !== entityDefaults[key];
	const anyModified = $derived(CRITERIA.some(({ key }) => isModified(key)));
</script>

{#snippet trend(from: number, to: number, lowerIsBetter: boolean)}
	{#if Number.isFinite(from) && Number.isFinite(to) && from !== to}
		{@const improved = lowerIsBetter ? to < from : to > from}
		<i
			class="fa-solid {to > from ? 'fa-arrow-up' : 'fa-arrow-down'} ml-1 text-[10px] {improved
				? 'text-success-600-400'
				: 'text-error-600-400'}"
			title={improved
				? m.residualImproved({ value: String(from) })
				: m.residualWorsened({ value: String(from) })}
		></i>
	{/if}
{/snippet}

<div class="card p-4 bg-surface-50-950 border border-surface-200-800 shadow-sm">
	<h3 class="font-semibold text-surface-700-300 mb-3 flex items-center gap-2">
		<i class="fa-solid fa-gauge-high text-purple-500"></i>
		{m.stakeholderCriticalityAssessment()}
	</h3>
	<table class="w-full text-sm">
		<thead>
			<tr class="text-surface-600-400 border-b border-surface-200-800">
				<th class="text-left font-medium py-1"></th>
				{#if hasEntityDefaults}
					<th class="text-center font-medium py-1">{m.entity()}</th>
				{/if}
				<th class="text-center font-medium py-1">{m.current()}</th>
				<th class="text-center font-medium py-1">{m.residual()}</th>
			</tr>
		</thead>
		<tbody>
			{#each CRITERIA as { key, label, lowerIsBetter }}
				<tr class="border-b border-surface-100-900">
					<td class="py-1 text-surface-700-300">{label}</td>
					{#if hasEntityDefaults}
						<td class="py-1 text-center text-surface-500">{entityDefaults[key]}</td>
					{/if}
					<td class="py-1 text-center">
						{#if isModified(key)}
							<span
								class="inline-flex items-center gap-1 rounded px-1.5 font-semibold text-primary-700-300 bg-primary-500/10"
								title={m.modifiedFromEntityDefault({ value: String(entityDefaults[key]) })}
							>
								{current[key]}
								<i class="fa-solid fa-thumbtack text-[10px]"></i>
							</span>
						{:else}
							{current[key]}
						{/if}
					</td>
					<td class="py-1 text-center">
						{residual[key]}{@render trend(current[key], residual[key], lowerIsBetter)}
					</td>
				</tr>
			{/each}
			<tr class="font-semibold">
				<td class="pt-2 text-surface-700-300">{m.criticality()}</td>
				{#if hasEntityDefaults}
					<td class="pt-2 text-center text-surface-500">{criticality(entityDefaults)}</td>
				{/if}
				<td class="pt-2 text-center">
					{#if anyModified}
						<span
							class="inline-flex items-center gap-1 rounded px-1.5 text-primary-700-300 bg-primary-500/10"
							title={m.criticalityModifiedFromEntity()}
						>
							{criticality(current)}
							<i class="fa-solid fa-thumbtack text-[10px]"></i>
						</span>
					{:else}
						{criticality(current)}
					{/if}
				</td>
				<td class="pt-2 text-center">
					{criticality(residual)}{@render trend(
						Number(criticality(current)),
						Number(criticality(residual)),
						true
					)}
				</td>
			</tr>
		</tbody>
	</table>
	{#if anyModified}
		<p class="mt-3 text-xs text-surface-600-400">
			<i class="fa-solid fa-thumbtack text-[10px] text-primary-500"></i>
			{m.stakeholderCriteriaModifiedLegend()}
		</p>
	{/if}
</div>
