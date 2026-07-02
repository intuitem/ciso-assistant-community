<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		onclose,
		width = 'max-w-md',
		children
	}: { onclose: () => void; width?: string; children: Snippet } = $props();
</script>

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
	role="presentation"
	onclick={(e) => {
		if (e.target === e.currentTarget) onclose();
	}}
>
	<div class="w-full {width} rounded-2xl bg-surface-50-950 p-6 shadow-xl space-y-4">
		{@render children()}
	</div>
</div>
