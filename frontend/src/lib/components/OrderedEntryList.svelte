<script lang="ts">
	import * as m from '$paraglide/messages';

	interface Entry {
		ref_id: string;
		name: string;
	}

	interface Props {
		entries?: Entry[];
		debug?: boolean;
		onchange?: (entries: Entry[]) => void;
	}

	let { entries = $bindable([]), debug = false, onchange }: Props = $props();

	let newRefId = $state('');
	let newName = $state('');
	let draggedIndex: number | null = $state(null);

	function addEntry() {
		if (newRefId.trim() && newName.trim()) {
			entries = [...entries, { ref_id: newRefId.trim(), name: newName.trim() }];
			newRefId = '';
			newName = '';
			onchange?.(entries);
		}
	}

	function deleteEntry(index: number) {
		entries = entries.filter((_, i) => i !== index);
		onchange?.(entries);
	}

	function updateEntry(index: number, field: 'ref_id' | 'name', value: string) {
		entries = entries.map((entry, i) => (i === index ? { ...entry, [field]: value } : entry));
		onchange?.(entries);
	}

	function handleDragStart(index: number) {
		draggedIndex = index;
	}

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
	}

	function handleDrop(e: DragEvent, dropIndex: number) {
		e.preventDefault();
		if (draggedIndex === null || draggedIndex === dropIndex) return;

		const newEntries = [...entries];
		const [draggedItem] = newEntries.splice(draggedIndex, 1);
		newEntries.splice(dropIndex, 0, draggedItem);

		entries = newEntries;
		draggedIndex = null;
		onchange?.(entries);
	}

	function handleDragEnd() {
		draggedIndex = null;
	}
</script>

<div class="space-y-4 border-2 border-dashed border-gray-300 rounded-lg p-4">
	<!-- Add Entry Form -->
	<div class="flex gap-2">
		<input
			type="text"
			bind:value={newRefId}
			placeholder={m.orderedEntryListRefIdPlaceholder()}
			class="input px-3 py-2 border border-gray-300 rounded w-1/3"
			onkeydown={(e) => e.key === 'Enter' && addEntry()}
		/>
		<input
			type="text"
			bind:value={newName}
			placeholder={m.orderedEntryListNamePlaceholder()}
			class="input px-3 py-2 border border-gray-300 rounded w-2/3"
			onkeydown={(e) => e.key === 'Enter' && addEntry()}
		/>
		<button
			type="button"
			class="btn bg-blue-600 text-white hover:bg-blue-700 px-4 py-2 rounded font-medium transition-colors whitespace-nowrap"
			onclick={addEntry}
		>
			{m.orderedEntryListAddButton()}
		</button>
	</div>

	<!-- Entries List -->
	<div class="space-y-2" role="list">
		{#if entries.length === 0}
			<div class="card bg-white p-4 shadow-sm text-center text-gray-500">
				{m.orderedEntryListEmptyState()}
			</div>
		{:else}
			{#each entries as entry, index (entry.ref_id + '-' + index)}
				<div
					class="card bg-white p-4 shadow-sm flex items-center gap-3 cursor-move hover:bg-gray-50 transition-colors mx-2"
					class:opacity-50={draggedIndex === index}
					draggable="true"
					ondragstart={() => handleDragStart(index)}
					ondragover={handleDragOver}
					ondrop={(e) => handleDrop(e, index)}
					ondragend={handleDragEnd}
					role="listitem"
				>
					<div class="flex-none">
						<span class="text-sm font-semibold text-gray-500 w-6 text-center">{index + 1}</span>
					</div>
					<div class="flex-none">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-5 w-5 text-gray-400"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 8h16M4 16h16"
							/>
						</svg>
					</div>
					<div class="flex-1 flex gap-4">
						<div class="w-1/3">
							<input
								type="text"
								value={entry.ref_id}
								class="input px-2 py-1 border border-transparent hover:border-gray-300 focus:border-blue-500 rounded w-full font-medium bg-transparent"
								onchange={(e) => updateEntry(index, 'ref_id', e.currentTarget.value)}
							/>
						</div>
						<div class="w-2/3">
							<input
								type="text"
								value={entry.name}
								class="input px-2 py-1 border border-transparent hover:border-gray-300 focus:border-blue-500 rounded w-full bg-transparent"
								onchange={(e) => updateEntry(index, 'name', e.currentTarget.value)}
							/>
						</div>
					</div>
					<button
						type="button"
						class="btn-sm text-red-600 hover:bg-red-50 px-3 py-1 rounded text-sm transition-colors"
						onclick={() => deleteEntry(index)}
						aria-label={m.orderedEntryListDeleteAriaLabel()}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-4 w-4"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
							/>
						</svg>
					</button>
				</div>
			{/each}
		{/if}
	</div>

	<!-- Debug Mode -->
	{#if debug}
		<div class="card bg-white p-4 shadow-sm">
			<h3 class="text-lg font-semibold mb-2">{m.orderedEntryListDebugTitle()}</h3>
			<pre class="bg-gray-100 p-3 rounded text-xs overflow-x-auto font-mono">{JSON.stringify(
					entries,
					null,
					2
				)}</pre>
		</div>
	{/if}
</div>
