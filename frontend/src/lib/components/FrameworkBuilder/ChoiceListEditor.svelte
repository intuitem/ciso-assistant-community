<script lang="ts">
	import { getBuilderContext, type QuestionChoice } from './builder-state';

	interface Props {
		choices: QuestionChoice[];
		sectionIndex: number;
		reqIndex: number;
		qIndex: number;
		implementationGroups?: Record<string, unknown>[] | null;
		minScore?: number;
		maxScore?: number;
	}

	let {
		choices,
		sectionIndex,
		reqIndex,
		qIndex,
		implementationGroups = null,
		minScore = 0,
		maxScore = 100
	}: Props = $props();

	const builder = getBuilderContext();
	const { errors: errorsStore } = builder;
	let draggedIndex: number | null = $state(null);
	let expandedIndex: number | null = $state(null);
	let confirmDeleteIndex: number | null = $state(null);

	async function saveField(choiceId: string, field: string, value: unknown) {
		await builder.updateChoice(choiceId, { [field]: value });
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
		builder.reorderChoices(sectionIndex, reqIndex, qIndex, draggedIndex, dropIndex);
		draggedIndex = null;
	}

	function handleDragEnd() {
		draggedIndex = null;
	}
</script>

<div class="space-y-1.5">
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-gray-500 uppercase tracking-wider">Choices</span>
		<button
			type="button"
			class="text-xs text-blue-600 hover:text-blue-700 font-medium"
			onclick={() => builder.addChoice(sectionIndex, reqIndex, qIndex)}
		>
			<i class="fa-solid fa-plus mr-1"></i>Add choice
		</button>
	</div>

	{#each choices as choice, index (choice.id)}
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

				{#if choice.color}
					<span
						class="w-3 h-3 rounded-full shrink-0 border border-gray-200"
						style="background-color: {choice.color}"
					></span>
				{/if}

				<input
					type="text"
					value={choice.value ?? ''}
					placeholder="Choice text..."
					class="flex-1 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-1 py-0.5 text-sm outline-none transition-colors"
					onblur={(e) => saveField(choice.id, 'value', e.currentTarget.value)}
				/>

				{#if choice.add_score != null}
					<span class="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
						+{choice.add_score}
					</span>
				{/if}

				<button
					type="button"
					class="text-gray-400 hover:text-gray-600 text-xs"
					onclick={() => (expandedIndex = expandedIndex === index ? null : index)}
				>
					<i class="fa-solid {expandedIndex === index ? 'fa-chevron-up' : 'fa-chevron-down'}"></i>
				</button>

				{#if confirmDeleteIndex === index}
					<button
						type="button"
						class="text-xs text-red-600 font-medium"
						onclick={() => {
							builder.deleteChoice(sectionIndex, reqIndex, qIndex, index);
							confirmDeleteIndex = null;
						}}
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
								value={choice.ref_id ?? ''}
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none"
								onblur={(e) => saveField(choice.id, 'ref_id', e.currentTarget.value)}
							/>
						</label>
						<label class="block">
							<span class="text-xs text-gray-500">Score</span>
							<input
								type="number"
								value={choice.add_score ?? ''}
								min={minScore}
								max={maxScore}
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none"
								onblur={(e) =>
									saveField(
										choice.id,
										'add_score',
										e.currentTarget.value ? Number(e.currentTarget.value) : null
									)}
							/>
						</label>
					</div>

					<div class="grid grid-cols-2 gap-2">
						<label class="block">
							<span class="text-xs text-gray-500">Result</span>
							<select
								value={choice.compute_result ?? ''}
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none"
								onchange={(e) =>
									saveField(choice.id, 'compute_result', e.currentTarget.value || null)}
							>
								<option value="">None</option>
								<option value="compliant">Compliant</option>
								<option value="non_compliant">Non-compliant</option>
								<option value="partially_compliant">Partially compliant</option>
								<option value="not_applicable">Not applicable</option>
							</select>
						</label>
						<label class="block">
							<span class="text-xs text-gray-500">Color</span>
							<div class="flex items-center gap-2">
								<input
									type="color"
									value={choice.color ?? '#6b7280'}
									class="w-8 h-8 rounded border border-gray-200 cursor-pointer"
									onchange={(e) => saveField(choice.id, 'color', e.currentTarget.value)}
								/>
								{#if choice.color}
									<button
										type="button"
										class="text-xs text-gray-400 hover:text-gray-600"
										onclick={() => saveField(choice.id, 'color', null)}
									>
										Clear
									</button>
								{/if}
							</div>
						</label>
					</div>

					{#if implementationGroups && implementationGroups.length > 0}
						<div>
							<span class="text-xs text-gray-500">Implementation Groups</span>
							<div class="flex flex-wrap gap-1 mt-1">
								{#each implementationGroups as ig}
									{@const refId = (ig as Record<string, string>).ref_id}
									{@const selected = (choice.select_implementation_groups ?? []).includes(refId)}
									<button
										type="button"
										class="text-xs px-2 py-0.5 rounded-full border transition-colors {selected
											? 'bg-blue-100 border-blue-300 text-blue-700'
											: 'bg-gray-50 border-gray-200 text-gray-500 hover:border-gray-300'}"
										onclick={() => {
											const current = choice.select_implementation_groups ?? [];
											const next = selected
												? current.filter((g: string) => g !== refId)
												: [...current, refId];
											saveField(choice.id, 'select_implementation_groups', next);
										}}
									>
										{refId}
									</button>
								{/each}
							</div>
						</div>
					{/if}

					<label class="block">
						<span class="text-xs text-gray-500">Description</span>
						<textarea
							value={choice.description ?? ''}
							rows="2"
							class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none resize-none"
							onblur={(e) => saveField(choice.id, 'description', e.currentTarget.value || null)}
						></textarea>
					</label>
				</div>
			{/if}
		</div>

		{#if $errorsStore.has(`choice-${choice.id}`)}
			<p class="text-xs text-red-600 px-1">{$errorsStore.get(`choice-${choice.id}`)}</p>
		{/if}
	{/each}

	{#if choices.length === 0}
		<p class="text-xs text-gray-400 text-center py-2">No choices yet. Add one above.</p>
	{/if}
</div>
