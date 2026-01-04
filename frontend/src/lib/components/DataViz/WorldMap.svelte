<script lang="ts">
	import { Orientation, Scale, TopoJSONMap, MapProjection } from '@unovis/ts';
	import { WorldMapTopoJSON } from '@unovis/ts/maps';
	import { VisSingleContainer, VisTopoJSONMap, VisTooltip } from '@unovis/svelte';

	let { data } = $props();
	const mapData = { areas: data };

	const tooltipTriggers = {
		[TopoJSONMap.selectors.feature]: (d) =>
			`${d.properties.name}: ${d.data?.count ? d.data?.count : 'no data'}`
	};

	let useEqualEarth = $state(true);
	const projection = $derived(
		useEqualEarth ? MapProjection.EqualEarth() : MapProjection.Mercator()
	);
</script>

<div class="w-full">
	<div class="flex justify-end mb-2">
		<label class="flex items-center gap-2 text-sm text-surface-600 cursor-pointer">
			<input type="checkbox" class="checkbox" bind:checked={useEqualEarth} />
			<span>{useEqualEarth ? 'Equal Earth' : 'Mercator'}</span>
		</label>
	</div>
	{#key useEqualEarth}
		<VisSingleContainer data={mapData} height={500} duration={0}>
			<VisTopoJSONMap topojson={WorldMapTopoJSON} {projection} />
			<VisTooltip triggers={tooltipTriggers} />
		</VisSingleContainer>
	{/key}
</div>
