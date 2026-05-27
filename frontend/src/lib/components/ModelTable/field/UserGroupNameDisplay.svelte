<script lang="ts">
	let { cell, meta }: { cell: string; meta: { path: { str: string }[] } } = $props();

	let display = $derived.by(() => {
		const ancestors = meta.path.slice(0, -1).map((f) => f.str);
		if (ancestors.length > 4) {
			ancestors.splice(1, ancestors.length - 4, '...');
		}
		return [...ancestors, cell].join(' / ');
	});
</script>

<span>{display}</span>
