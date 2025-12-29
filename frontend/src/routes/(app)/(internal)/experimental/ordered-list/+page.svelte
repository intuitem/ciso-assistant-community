<script lang="ts">
	import OrderedEntryList from '$lib/components/OrderedEntryList.svelte';

	let entries = $state([
		{ ref_id: 'REF-001', name: 'First Entry' },
		{ ref_id: 'REF-002', name: 'Second Entry' },
		{ ref_id: 'REF-003', name: 'Third Entry' }
	]);

	let debugMode = $state(true);

	function handleChange(newEntries: Array<{ ref_id: string; name: string }>) {
		console.log('Entries updated:', newEntries);
	}
</script>

<div class="container mx-auto p-6 max-w-4xl">
	<div class="mb-6">
		<h1 class="text-3xl font-bold mb-2">Ordered Entry List - Test Page</h1>
		<p class="text-gray-600">
			Test the drag-and-drop ordered entry list component. Add, reorder, and delete entries.
		</p>
	</div>

	<div class="mb-4">
		<label class="flex items-center gap-2 cursor-pointer">
			<input
				type="checkbox"
				bind:checked={debugMode}
				class="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
			/>
			<span>Enable Debug Mode</span>
		</label>
	</div>

	<OrderedEntryList bind:entries debug={debugMode} onchange={handleChange} />
</div>
