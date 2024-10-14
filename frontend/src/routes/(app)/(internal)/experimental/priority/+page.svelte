<script lang="ts">
	import { Position, Scale, Scatter } from '@unovis/ts';
	import { VisXYContainer, VisScatter, VisAxis, VisTooltip, VisBulletLegend } from '@unovis/svelte';
	export type DataRecord = {
		major: string;
		category: string;
		total: number;
		effort: number;
		cost: number;
	};

	export const palette = [
		'#04c0c7',
		'#e7871a',
		'#da348f',
		'#9089fa',
		'#47e26f',
		'#2780eb',
		'#6f38b1',
		'#268d6c',
		'#d11d55',
		'#ffcc00',
		'#a0d6e5',
		'#f45a6d'
	];

	export const data = [
		{
			major: 'Control 1',
			category: 'Govern',
			total: 12,
			effort: 0,
			cost: 0
		},
		{
			major: 'Control 2',
			category: 'Govern',
			total: 9,
			effort: 0,
			cost: 0
		},
		{
			major: 'Control 3',
			category: 'Protect',
			total: 33,
			effort: 1,
			cost: 0
		},
		{
			major: 'Control 4',
			category: 'Detect',
			total: 10,
			effort: 2,
			cost: 0
		}
	].sort((a, b) => b.total - a.total);

	const categories = [...new Set(data.map((d: DataRecord) => d.category))].sort();
	const colorScale = Scale.scaleOrdinal(palette).domain(categories);
	const formatNumber = Intl.NumberFormat('en', { notation: 'compact' }).format;

	// scatter props
	const x = (d: DataRecord) => d.cost;
	const y = (d: DataRecord) => d.effort;
	const color = (d: DataRecord) => colorScale(d.category);
	const size = (d: DataRecord) => d.total;
	const label = (d: DataRecord) => formatNumber(d.total);

	const legendItems = categories.map((v) => ({ name: v, color: colorScale(v) }));
	const triggers = {
		[Scatter.selectors.point]: (d: DataRecord) => `
      <b>${d.major}</b><br/>Attached items: ${d.total.toLocaleString()}
    `
	};
</script>

<div class="bg-white p-4">
	<h2>American College Graduates, 2010-2012</h2>
	<VisBulletLegend items={legendItems} />
	<VisXYContainer {data} height={600} scaleByDomain={true}>
		<VisScatter
			{x}
			{y}
			{color}
			{size}
			{label}
			labelPosition={Position.Bottom}
			sizeRange={[10, 50]}
			cursor="pointer"
		/>
		<VisAxis type="x" label="Cost ($)" tickFormat={formatNumber} />
		<VisAxis excludeFromDomainCalculation type="y" label="Effort" tickPadding={0} />
		<VisTooltip {triggers} />
	</VisXYContainer>
</div>
