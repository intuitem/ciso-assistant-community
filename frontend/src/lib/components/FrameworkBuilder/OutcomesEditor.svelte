<script lang="ts">
	import { getTranslation, withTranslation, type OutcomeRule } from './builder-state';
	import { createDragHandlers } from './builder-utils.svelte';
	import ConfirmAction from './ConfirmAction.svelte';

	interface Props {
		outcomes: OutcomeRule[];
		onupdate: (rules: OutcomeRule[]) => void;
		activeLanguage?: string | null;
	}

	let { outcomes, onupdate, activeLanguage = null }: Props = $props();

	let rules: OutcomeRule[] = $state(outcomes.map((r) => ({ ...r })));
	let expandedIndex: number | null = $state(null);
	let showCelRef: boolean = $state(false);

	// Sync from parent when outcomes prop changes (e.g. after reload)
	$effect(() => {
		rules = outcomes.map((r) => ({ ...r }));
	});

	function persist() {
		onupdate(rules.map((r) => ({ ...r })));
	}

	function addRule() {
		rules = [...rules, { ref_id: '', annotation: '', color: null, expression: '' }];
		expandedIndex = rules.length - 1;
		persist();
	}

	function deleteRule(index: number) {
		rules = rules.filter((_, i) => i !== index);
		if (expandedIndex === index) expandedIndex = null;
		persist();
	}

	const drag = createDragHandlers((from, to) => {
		const copy = [...rules];
		const [moved] = copy.splice(from, 1);
		copy.splice(to, 0, moved);
		rules = copy;
		persist();
	});
</script>

<div class="space-y-1.5">
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-gray-500 uppercase tracking-wider">Outcome rules</span>
		<button
			type="button"
			class="text-xs text-blue-600 hover:text-blue-700 font-medium"
			onclick={addRule}
		>
			<i class="fa-solid fa-plus mr-1"></i>Add rule
		</button>
	</div>

	{#each rules as rule, index (index)}
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

				{#if rule.color}
					<span
						class="w-3 h-3 rounded-full shrink-0 border border-gray-200"
						style="background-color: {rule.color}"
					></span>
				{/if}

				<span class="text-sm font-medium text-gray-700 truncate min-w-0">
					{rule.ref_id || 'Untitled rule'}
				</span>

				{#if rule.annotation}
					<span class="text-xs text-gray-400 truncate min-w-0">{rule.annotation}</span>
				{/if}

				<span class="ml-auto text-xs text-gray-400 font-mono truncate max-w-[200px]">
					{rule.expression || '...'}
				</span>

				<button
					type="button"
					class="text-gray-400 hover:text-gray-600 text-xs"
					onclick={() => (expandedIndex = expandedIndex === index ? null : index)}
				>
					<i class="fa-solid {expandedIndex === index ? 'fa-chevron-up' : 'fa-chevron-down'}"></i>
				</button>

				<ConfirmAction onconfirm={() => deleteRule(index)} />
			</div>

			<!-- Expanded details -->
			{#if expandedIndex === index}
				<div class="px-3 pb-3 pt-1 border-t border-gray-200 space-y-2">
					<div class="grid grid-cols-2 gap-2">
						<label class="block">
							<span class="text-xs text-gray-500">Ref ID</span>
							<input
								type="text"
								value={rule.ref_id}
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => {
									rules[index].ref_id = e.currentTarget.value;
									persist();
								}}
							/>
						</label>
						<label class="block">
							<span class="text-xs text-gray-500">Label</span>
							<input
								type="text"
								value={rule.annotation}
								placeholder="e.g. High compliance"
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => {
									rules[index].annotation = e.currentTarget.value;
									persist();
								}}
							/>
						</label>
					</div>

					<label class="block">
						<span class="text-xs text-gray-500">CEL Expression</span>
						<textarea
							value={rule.expression}
							placeholder={'e.g. assessment.score_sum >= 150 or "true" for catch-all'}
							rows="2"
							class="w-full text-sm font-mono border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 resize-none"
							onblur={(e) => {
								rules[index].expression = e.currentTarget.value;
								persist();
							}}
						></textarea>
					</label>

					<label class="block">
						<span class="text-xs text-gray-500">Color</span>
						<div class="flex items-center gap-2">
							<input
								type="color"
								value={rule.color ?? '#6b7280'}
								class="w-8 h-8 rounded border border-gray-200 cursor-pointer"
								onchange={(e) => {
									rules[index].color = e.currentTarget.value;
									persist();
								}}
							/>
							{#if rule.color}
								<button
									type="button"
									class="text-xs text-gray-400 hover:text-gray-600"
									onclick={() => {
										rules[index].color = null;
										persist();
									}}
								>
									Clear
								</button>
							{/if}
						</div>
					</label>

					{#if activeLanguage}
						{@const lang = activeLanguage}
						<label class="block border-t border-gray-200 pt-2">
							<span class="text-xs text-blue-500">{lang.toUpperCase()} Label</span>
							<input
								type="text"
								value={getTranslation(rule.translations, lang, 'annotation')}
								placeholder="Translate label..."
								class="w-full text-sm border border-blue-100 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => {
									rules[index].translations = withTranslation(
										rules[index].translations,
										lang,
										'annotation',
										e.currentTarget.value
									);
									persist();
								}}
							/>
						</label>
					{/if}
				</div>
			{/if}
		</div>
	{/each}

	{#if rules.length === 0}
		<p class="text-xs text-gray-400 text-center py-2">No outcome rules yet. Add one above.</p>
	{/if}

	<p class="text-xs text-gray-400">
		Rules are evaluated in order. First matching rule wins. Use <code
			class="font-mono bg-gray-100 px-1 rounded">true</code
		> as a catch-all.
	</p>

	<button
		type="button"
		class="text-xs text-gray-400 hover:text-gray-600"
		onclick={() => (showCelRef = !showCelRef)}
	>
		<i class="fa-solid {showCelRef ? 'fa-chevron-up' : 'fa-chevron-down'} mr-1"></i>
		CEL context reference
	</button>
	{#if showCelRef}
		<div
			class="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-lg p-3 font-mono space-y-1"
		>
			<div><span class="text-gray-700">assessment.score_sum</span> — total points scored</div>
			<div><span class="text-gray-700">assessment.score_max</span> — total possible points</div>
			<div>
				<span class="text-gray-700">assessment.answered_count</span> — answered requirements
			</div>
			<div>
				<span class="text-gray-700">assessment.total_count</span> — total assessable requirements
			</div>
			<div>
				<span class="text-gray-700">requirements["urn:..."].score</span> — requirement score
			</div>
			<div>
				<span class="text-gray-700">requirements["urn:..."].max_score</span> — requirement max score
			</div>
			<div>
				<span class="text-gray-700">requirements["urn:..."].result</span> — requirement result
			</div>
			<div>
				<span class="text-gray-700">requirements["urn:..."].status</span> — requirement status
			</div>
			<div class="pt-1 border-t border-gray-200 mt-1">
				<span class="text-gray-700">ref_ids["REF_ID"].score</span> — requirement score (by ref ID, works
				across copies)
			</div>
			<div>
				<span class="text-gray-700">ref_ids["REF_ID"].max_score / .result / .status</span> — same fields
				as above
			</div>
		</div>
	{/if}
</div>
