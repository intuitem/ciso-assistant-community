<script lang="ts">
	import { Orientation, Scale, TopoJSONMap, MapProjection } from '@unovis/ts';
	import { WorldMapTopoJSON } from '@unovis/ts/maps';
	import { VisSingleContainer, VisTopoJSONMap, VisTooltip } from '@unovis/svelte';

	let { data } = $props();
	const mapData = { areas: data };

	const tooltipTriggers = {
		[TopoJSONMap.selectors.feature]: (d) =>
			`${d.properties.name}: ${d.data.count ? d.data.count : 'no data'}`
	};
</script>

<div class="">
	<VisSingleContainer data={mapData} height={600} duration={0}>
		<VisTopoJSONMap topojson={WorldMapTopoJSON} projection={MapProjection.EqualEarth()} />
		<VisTooltip triggers={tooltipTriggers} />
	</VisSingleContainer>
</div>
