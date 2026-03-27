<script lang="ts">
	import { getTranslation, withTranslation, type ImplementationGroup } from './builder-state';
	import { createDragHandlers } from './builder-utils';
	import ConfirmAction from './ConfirmAction.svelte';

	interface Props {
		groups: ImplementationGroup[];
		onupdate: (groups: ImplementationGroup[]) => void;
		activeLanguage?: string | null;
	}

	let { groups, onupdate, activeLanguage = null }: Props = $props();

	let items: ImplementationGroup[] = $state(groups.map((g) => ({ ...g })));
	let expandedIndex: number | null = $state(null);

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
		if (expandedIndex === index) expandedIndex = null;
		persist();
	}

	const drag = createDragHandlers((from, to) => {
		const copy = [...items];
		const [moved] = copy.splice(from, 1);
		copy.splice(to, 0, moved);
		items = copy;
		persist();
	});
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
			class="border border-gray-200 rounded-lg bg-gray-50/50 transition-all {drag.draggedIndex ===
			index
				? 'opacity-50'
				: ''}"
			draggable="true"
			ondragstart={() => drag.handleDragStart(index)}
			ondragover={drag.handleDragOver}
			ondrop={(e) => drag.handleDrop(e, index)}
			ondragend={drag.handleDragEnd}
			role="listitem"
		>
			<!-- Collapsed row -->
			<div class="flex items-center gap-2 px-3 py-2">
				<span class="cursor-grab text-gray-300 hover:text-gray-500">
					<i class="fa-solid fa-grip-vertical text-xs"></i>
				</span>

				{#if group.name}
					<span class="text-sm font-medium text-gray-700 truncate min-w-0">
						{group.name || 'Untitled group'}
					</span>
				{/if}

				<span class="text-xs text-gray-400 truncate min-w-0">{group.ref_id}</span>

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

				<ConfirmAction onconfirm={() => deleteGroup(index)} />
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

					{#if activeLanguage}
						{@const lang = activeLanguage}
						<div class="border-t border-gray-200 pt-2 space-y-1.5">
							<span class="text-[10px] text-blue-500 font-medium uppercase"
								>{lang.toUpperCase()} translation</span
							>
							<div class="grid grid-cols-2 gap-2">
								<label class="block">
									<span class="text-xs text-blue-500">Name</span>
									<input
										type="text"
										value={getTranslation(group.translations, lang, 'name')}
										placeholder="Translate name..."
										class="w-full text-sm border border-blue-100 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
										onblur={(e) => {
											items[index].translations = withTranslation(
												items[index].translations,
												lang,
												'name',
												e.currentTarget.value
											);
											persist();
										}}
									/>
								</label>
								<label class="block">
									<span class="text-xs text-blue-500">Description</span>
									<input
										type="text"
										value={getTranslation(group.translations, lang, 'description')}
										placeholder="Translate description..."
										class="w-full text-sm border border-blue-100 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
										onblur={(e) => {
											items[index].translations = withTranslation(
												items[index].translations,
												lang,
												'description',
												e.currentTarget.value
											);
											persist();
										}}
									/>
								</label>
							</div>
						</div>
					{/if}
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
