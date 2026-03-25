<script lang="ts">
	import type { ImplementationGroup } from './builder-state';

	interface Props {
		groups: ImplementationGroup[];
		onupdate: (groups: ImplementationGroup[]) => void;
	}

	let { groups, onupdate }: Props = $props();

	let items: ImplementationGroup[] = $state(groups.map((g) => ({ ...g })));
	let draggedIndex: number | null = $state(null);
	let expandedIndex: number | null = $state(null);
	let confirmDeleteIndex: number | null = $state(null);

	// Sync from parent when groups prop changes (e.g. after reload)
	$effect(() => {
		items = groups.map((g) => ({ ...g }));
	});

	function persist() {
		onupdate(items.map((g) => ({ ...g })));
	}

	function addGroup() {
		items = [...items, { ref_id: '', name: '', description: '', default_selected: false }];
		expandedIndex = items.length - 1;
		persist();
	}

	function deleteGroup(index: number) {
		items = items.filter((_, i) => i !== index);
		confirmDeleteIndex = null;
		if (expandedIndex === index) expandedIndex = null;
		persist();
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
		const copy = [...items];
		const [moved] = copy.splice(draggedIndex, 1);
		copy.splice(dropIndex, 0, moved);
		items = copy;
		draggedIndex = null;
		persist();
	}

	function handleDragEnd() {
		draggedIndex = null;
	}
</script>

<div class="space-y-1.5">
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-gray-500 uppercase tracking-wider"
			>Implementation groups</span
		>
		<button
			type="button"
			class="text-xs text-blue-600 hover:text-blue-700 font-medium"
			onclick={addGroup}
		>
			<i class="fa-solid fa-plus mr-1"></i>Add group
		</button>
	</div>

	{#each items as group, index (index)}
		<div
			class="border border-gray-200 rounded-lg bg-gray-50/50 transition-all {draggedIndex === index
				? 'opacity-50'
				: ''}"
			draggable="true"
			ondragstart={() => handleDragStart(index)}
			ondragover={handleDragOver}
			ondrop={(e) => handleDrop(e, index)}
			ondragend={handleDragEnd}
			role="listitem"
		>
			<!-- Collapsed row -->
			<div class="flex items-center gap-2 px-3 py-2">
				<span class="cursor-grab text-gray-300 hover:text-gray-500">
					<i class="fa-solid fa-grip-vertical text-xs"></i>
				</span>

				<span class="text-sm font-medium text-gray-700 truncate min-w-0">
					{group.ref_id || 'Untitled group'}
				</span>

				{#if group.name}
					<span class="text-xs text-gray-400 truncate min-w-0">{group.name}</span>
				{/if}

				{#if group.default_selected}
					<span
						class="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 border border-green-200"
						>default</span
					>
				{/if}

				<button
					type="button"
					class="ml-auto text-gray-400 hover:text-gray-600 text-xs"
					onclick={() => (expandedIndex = expandedIndex === index ? null : index)}
				>
					<i class="fa-solid {expandedIndex === index ? 'fa-chevron-up' : 'fa-chevron-down'}"></i>
				</button>

				{#if confirmDeleteIndex === index}
					<button
						type="button"
						class="text-xs text-red-600 font-medium"
						onclick={() => deleteGroup(index)}
					>
						Confirm
					</button>
					<button
						type="button"
						class="text-xs text-gray-500"
						onclick={() => (confirmDeleteIndex = null)}
					>
						Cancel
					</button>
				{:else}
					<button
						type="button"
						class="text-gray-300 hover:text-red-500 text-xs transition-colors"
						onclick={() => (confirmDeleteIndex = index)}
					>
						<i class="fa-solid fa-trash"></i>
					</button>
				{/if}
			</div>

			<!-- Expanded details -->
			{#if expandedIndex === index}
				<div class="px-3 pb-3 pt-1 border-t border-gray-200 space-y-2">
					<div class="grid grid-cols-2 gap-2">
						<label class="block">
							<span class="text-xs text-gray-500">Ref ID</span>
							<input
								type="text"
								value={group.ref_id}
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => {
									items[index].ref_id = e.currentTarget.value;
									persist();
								}}
							/>
						</label>
						<label class="block">
							<span class="text-xs text-gray-500">Name</span>
							<input
								type="text"
								value={group.name}
								placeholder="e.g. Tier 1"
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => {
									items[index].name = e.currentTarget.value;
									persist();
								}}
							/>
						</label>
					</div>

					<label class="block">
						<span class="text-xs text-gray-500">Description</span>
						<textarea
							value={group.description}
							placeholder="Description of this implementation group"
							rows="2"
							class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 resize-none"
							onblur={(e) => {
								items[index].description = e.currentTarget.value;
								persist();
							}}
						></textarea>
					</label>

					<label class="flex items-center gap-2">
						<input
							type="checkbox"
							checked={group.default_selected ?? false}
							onchange={(e) => {
								items[index].default_selected = e.currentTarget.checked;
								persist();
							}}
							class="w-3.5 h-3.5 rounded border-gray-300"
						/>
						<span class="text-xs text-gray-500">Selected by default</span>
					</label>
				</div>
			{/if}
		</div>
	{/each}

	{#if items.length === 0}
		<p class="text-xs text-gray-400 text-center py-2">
			No implementation groups defined. Add one above.
		</p>
	{/if}
</div>
