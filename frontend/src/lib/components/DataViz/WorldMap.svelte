<script lang="ts">
	import { Orientation, Scale, TopoJSONMap, MapProjection } from '@unovis/ts';
	import { WorldMapTopoJSON } from '@unovis/ts/maps';
	import { VisSingleContainer, VisTopoJSONMap, VisTooltip } from '@unovis/svelte';
	export let data;

	const palette = ['#E6B236', '#006E8D'];
	const mapData = { areas: data };

	// scale functions

	const tooltipTriggers = {
		[TopoJSONMap.selectors.feature]: (d) =>
			`${d.properties.name}: ${d.data.count ? d.data.count : 'no data'}`
	};
</script>

<div class="topojson-map">
	<!-- year slider -->
	<!-- topojson map -->
	<VisSingleContainer data={mapData} height={600} duration={0}>
		<VisTopoJSONMap
			topojson={WorldMapTopoJSON}
			mapFitToPoints
			projection={MapProjection.EqualEarth()}
		/>
		<VisTooltip triggers={tooltipTriggers} />
	</VisSingleContainer>
</div>

<style>
	.topojson-map,
	.year-slider {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
	}

	.year-slider {
		width: max-content;
		position: relative;
		margin-bottom: 20px;
	}

	.year-slider h2 {
		font-weight: 500;
	}

	.year-slider input {
		width: 75%;
	}

	.year-slider > input::before {
		position: absolute;
		content: attr(min);
		left: 0;
	}

	.year-slider > input::after {
		position: absolute;
		content: attr(max);
		right: 0;
	}
</style>
