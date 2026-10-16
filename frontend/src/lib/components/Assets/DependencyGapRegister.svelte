<script lang="ts">
	import { m } from '$paraglide/messages';
	import { formatGap, type DependencyGraph } from './dependency-graph';

	interface Props {
		graph: DependencyGraph;
		onselect: (id: string) => void;
	}

	let { graph, onselect }: Props = $props();

	const rows = $derived(
		graph.nodes
			.filter((n) => n.status === 'cause')
			.map((n) => {
				const impacted = (graph.impacts[n.id] ?? []).map((id) => graph.byId[id]);
				const primary = impacted.filter((i) => i.type === 'PR');
				const otherDomains = new Set(primary.map((i) => i.domain).filter((d) => d !== n.domain));
				return {
					node: n,
					primary: primary.length,
					impacted: impacted.length,
					otherDomains: otherDomains.size,
					assessed: impacted.filter((i) => graph.roots.includes(i.id)).length
				};
			})
			.sort((a, b) => b.assessed - a.assessed || b.primary - a.primary || b.impacted - a.impacted)
	);
</script>

<div class="h-full overflow-auto">
	{#if rows.length}
		<table class="w-full text-sm">
			<thead class="sticky top-0 bg-surface-50-950 text-left text-xs text-surface-600-400">
				<tr>
					<th class="p-2 font-medium">{m.dependencyCause()}</th>
					<th class="p-2 font-medium">{m.domain()}</th>
					<th class="p-2 font-medium">{m.failingObjectives()}</th>
					<th class="p-2 font-medium text-right">{m.assessedAssetsImpacted()}</th>
					<th class="p-2 font-medium text-right">{m.primaryAssetsImpacted()}</th>
					<th class="p-2 font-medium">{m.reach()}</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as row (row.node.id)}
					<tr
						class="border-t border-surface-200-800 cursor-pointer hover:bg-primary-500/10 align-top"
						tabindex="0"
						onclick={() => onselect(row.node.id)}
						onkeydown={(e) => e.key === 'Enter' && onselect(row.node.id)}
					>
						<td class="p-2">{row.node.label}</td>
						<td class="p-2">
							<span class="flex items-center gap-2">
								<span
									class="size-2.5 rounded-sm shrink-0"
									style:background={graph.domainColor[row.node.domain]}
								></span>
								{row.node.domain_name}
							</span>
						</td>
						<td class="p-2">
							<div class="flex flex-wrap gap-1">
								{#each row.node.gaps as gap (gap.objective)}
									<span class="badge preset-tonal-error font-mono text-xs">{formatGap(gap)}</span>
								{/each}
							</div>
						</td>
						<td class="p-2 text-right tabular-nums">{row.assessed}</td>
						<td class="p-2 text-right tabular-nums">{row.primary}</td>
						<td class="p-2">
							<div class="flex flex-wrap gap-1">
								{#if row.otherDomains}
									<span class="badge preset-tonal-primary text-xs"
										>{m.otherDomainsCount({ count: row.otherDomains })}</span
									>
								{/if}
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else}
		<p class="p-6 text-surface-600-400">{m.noCapabilityGaps()}</p>
	{/if}
</div>
