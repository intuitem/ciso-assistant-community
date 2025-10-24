<script lang="ts">
	import StackedBarsNormalized from '../Chart/StackedBarsNormalized.svelte';
	let { frameworksMappings } = $props();
	// frameworksMappings = frameworksMappings.response;
	const metrics = {
		names: frameworksMappings.map((f) => f.str),
		data: frameworksMappings.map((f) => [
			f.results.not_assessed || 0,
			f.results.partially_compliant || 0,
			f.results.non_compliant || 0,
			f.results.compliant || 0,
			f.results.not_applicable || 0
		]),
		uuids: frameworksMappings.map((f) => f.id)
	};

	for (let x = 0; x < metrics.data.length; x++) {
		let dataE = metrics.data[x];
		dataE[4] =
			frameworksMappings[x].assessable_requirements_count -
			dataE[0] -
			dataE[1] -
			dataE[2] -
			dataE[3];
	}
</script>

<StackedBarsNormalized
	names={metrics.names}
	data={metrics.data}
	title="Equivalence with other frameworks"
	uuids={metrics.uuids}
	seriesNames={[
		'compliant',
		'partially compliant',
		'non compliant',
		'not applicable',
		'not assessed'
	]}
	colors={['#86EFAC', '#FDE047', '#F87171', '#000000', '#D1D5DB']}
/>
