<script lang="ts">
	import { Timeline } from '@unovis/ts';
	import {
		VisXYContainer,
		VisBulletLegend,
		VisTooltip,
		VisTimeline,
		VisAxis
	} from '@unovis/svelte';

	import type { PageData } from './$types';
	export let data: PageData;
	type DataRecord = {
		name: string;
		startDate: number;
		endDate: number;
		description?: string;
	};

	const colorMap = data.data.colorMap;

	const tdata = data.data.entries.sort((p1, p2) => p1.startDate - p2.startDate) as DataRecord[];

	const labelWidth = 220;
	const dateFormatter = Intl.DateTimeFormat().format;

	function getTooltipText(_: string, i: number): string {
		const { startDate, endDate, description } = tdata[i];
		return `
      <div style="width:${labelWidth}px">
        <small>${[startDate, endDate].map(dateFormatter).join(' &#8594; ')}</small><br/>
        <code>${description}</code>
      </div>`;
	}

	const x = (d: DataRecord) => d.startDate;
	const length = (d: DataRecord) => d.endDate - d.startDate;
	const type = (d: DataRecord) => d.name;
	const color = (d: DataRecord) => colorMap[d.domain];

	const legendItems = Object.keys(colorMap).map((name, i) => ({ name, color: colorMap[name] }));
	const triggers = { [Timeline.selectors.label]: getTooltipText };
</script>

{#if data.data.entries.length > 0}
	<div class="bg-white p-4 h-full">
		<VisXYContainer data={tdata} height={800}>
			<h3>Applied controls timeline</h3>
			<div class="text-xs text-slate-500 mb-4">
				<i class="fa-solid fa-circle-info mr-2"></i>Start date and ETA must be set for items to
				render
			</div>
			<VisBulletLegend items={legendItems} />
			<VisTimeline
				{x}
				{length}
				{type}
				{color}
				alternatingRowColors={true}
				{labelWidth}
				showLabels={true}
				lineCap={true}
				showEmptySegments={true}
				rowHeight={30}
			/>
			<VisTooltip {triggers} />
			<VisAxis type="x" tickFormat={dateFormatter} />
		</VisXYContainer>
	</div>
{:else}
	<div class="p-4 text-slate-600">
		<i class="fa-solid fa-triangle-exclamation"></i> No available data. Make sure you have ETA and start
		dates on your controls.
	</div>
{/if}
