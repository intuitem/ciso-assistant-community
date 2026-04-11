<script lang="ts">
	import { tick } from 'svelte';
	import {
		getBuilderContext,
		getTranslation,
		withTranslation,
		type QuestionChoice
	} from './builder-state';
	import { createDragHandlers } from './builder-utils.svelte';
	import ConfirmAction from './ConfirmAction.svelte';

	interface Props {
		choices: QuestionChoice[];
		reqNodeId: string;
		qIndex: number;
		implementationGroups?: Record<string, unknown>[] | null;
		minScore?: number;
		maxScore?: number;
	}

	let {
		choices,
		reqNodeId,
		qIndex,
		implementationGroups = null,
		minScore = 0,
		maxScore = 100
	}: Props = $props();

	const builder = getBuilderContext();
	const { errors: errorsStore, activeLanguage: activeLanguageStore } = builder;
	const drag = createDragHandlers((from, to) =>
		builder.reorderChoices(reqNodeId, qIndex, from, to)
	);
	let expandedIndex: number | null = $state(null);

	let listEl: HTMLDivElement;

	async function saveField(choiceId: string, field: string, value: unknown) {
		await builder.updateChoice(choiceId, { [field]: value });
	}

	async function handleChoiceKeydown(e: KeyboardEvent, choice: QuestionChoice, index: number) {
		const input = e.currentTarget as HTMLInputElement;
		if (e.key === 'Enter') {
			e.preventDefault();
			const val = input.value.trim();
			if (!val) return;
			await saveField(choice.id, 'value', val);
			builder.addChoice(reqNodeId, qIndex);
			await tick();
			const inputs = listEl?.querySelectorAll<HTMLInputElement>('.choice-value-input');
			inputs?.[inputs.length - 1]?.focus();
		} else if (e.key === 'Backspace' && !input.value) {
			e.preventDefault();
			builder.deleteChoice(reqNodeId, qIndex, index);
			await tick();
			const inputs = listEl?.querySelectorAll<HTMLInputElement>('.choice-value-input');
			if (inputs && inputs.length > 0) {
				inputs[Math.min(index, inputs.length - 1)]?.focus();
			}
		}
	}
</script>

<div class="space-y-1.5" bind:this={listEl}>
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-gray-500 uppercase tracking-wider">Choices</span>
		<button
			type="button"
			class="text-xs text-blue-600 hover:text-blue-700 font-medium"
			onclick={() => builder.addChoice(reqNodeId, qIndex)}
		>
			<i class="fa-solid fa-plus mr-1"></i>Add choice
		</button>
	</div>

	{#each choices as choice, index (choice.id)}
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

				{#if choice.color}
					<span
						class="w-3 h-3 rounded-full shrink-0 border border-gray-200"
						style="background-color: {choice.color}"
					></span>
				{/if}

				{#if $activeLanguageStore}
					{@const lang = $activeLanguageStore}
					<span class="text-sm text-gray-400 truncate max-w-[40%]" title={choice.value ?? ''}
						>{choice.value ?? ''}</span
					>
					<input
						type="text"
						value={getTranslation(choice.translations, lang, 'value')}
						placeholder="Translate..."
						class="flex-1 bg-transparent border-0 border-b border-transparent hover:border-blue-300 focus:border-blue-500 px-1 py-0.5 text-sm outline-none transition-colors"
						onblur={(e) =>
							saveField(
								choice.id,
								'translations',
								withTranslation(choice.translations, lang, 'value', e.currentTarget.value)
							)}
					/>
				{:else}
					<input
						type="text"
						value={choice.value ?? ''}
						placeholder="Choice text..."
						class="choice-value-input flex-1 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-1 py-0.5 text-sm text-gray-900 outline-none transition-colors"
						onblur={(e) => saveField(choice.id, 'value', e.currentTarget.value)}
						onkeydown={(e) => handleChoiceKeydown(e, choice, index)}
					/>
				{/if}

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

				<ConfirmAction onconfirm={() => builder.deleteChoice(reqNodeId, qIndex, index)} />
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
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
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
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
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
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
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
							class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 resize-none"
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
