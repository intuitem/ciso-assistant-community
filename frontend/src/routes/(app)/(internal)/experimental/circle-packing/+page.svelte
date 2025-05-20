<script>
	import ForceCirclePacking from '$lib/components/DataViz/ForceCirclePacking.svelte';
	const data = {
		nodes: [
			{ name: 'some threat', value: 10, items: ['abc', 'mno', 'xyz'] },
			{ name: 'abc mno xyz', value: 5 },
			{ name: 'bar', value: 1 },
			{ name: 'baz', value: 1 }
		]
	};
</script>

<div class="h-screen">
	<ForceCirclePacking {data} />
</div>
