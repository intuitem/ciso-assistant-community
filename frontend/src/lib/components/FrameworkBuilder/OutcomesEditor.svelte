<script lang="ts">
	import { getTranslation, withTranslation, type OutcomeRule } from './builder-state';
	import { createDragHandlers } from './builder-utils.svelte';
	import ConfirmAction from './ConfirmAction.svelte';
	import { m } from '$paraglide/messages';

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

	// Split the hint message around its {trueLiteral} placeholder so we can render
	// a real <code> element in the middle without resorting to {@html}. The NUL
	// sentinel is safe because translations are baked at build time.
	const hintParts = $derived(m.builderOutcomeRulesHint({ trueLiteral: '\x00' }).split('\x00'));
</script>

<div class="space-y-1.5">
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-surface-600-400 uppercase tracking-wider"
			>{m.builderOutcomeRules()}</span
		>
		<button
			type="button"
			class="text-xs text-blue-600 hover:text-blue-700 font-medium"
			onclick={addRule}
		>
			<i class="fa-solid fa-plus mr-1"></i>{m.builderAddRule()}
		</button>
	</div>

	{#each rules as rule, index (index)}
		<div
			class="border border-surface-200-800 rounded-lg bg-surface-50-950/50 transition-all {drag.draggedIndex ===
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
				<span class="cursor-grab text-gray-300 hover:text-surface-600-400">
					<i class="fa-solid fa-grip-vertical text-xs"></i>
				</span>

				{#if rule.color}
					<span
						class="w-3 h-3 rounded-full shrink-0 border border-surface-200-800"
						style="background-color: {rule.color}"
					></span>
				{/if}

				<span class="text-sm font-medium text-surface-700-300 truncate min-w-0">
					{rule.ref_id || m.builderUntitledRule()}
				</span>

				{#if rule.annotation}
					<span class="text-xs text-surface-500 truncate min-w-0">{rule.annotation}</span>
				{/if}

				<span class="ml-auto text-xs text-surface-500 font-mono truncate max-w-[200px]">
					{rule.expression || '...'}
				</span>

				<button
					type="button"
					class="text-surface-500 hover:text-surface-600-400 text-xs"
					onclick={() => (expandedIndex = expandedIndex === index ? null : index)}
				>
					<i class="fa-solid {expandedIndex === index ? 'fa-chevron-up' : 'fa-chevron-down'}"></i>
				</button>

				<ConfirmAction onconfirm={() => deleteRule(index)} />
			</div>

			<!-- Expanded details -->
			{#if expandedIndex === index}
				<div class="px-3 pb-3 pt-1 border-t border-surface-200-800 space-y-2">
					<div class="grid grid-cols-2 gap-2">
						<label class="block">
							<span class="text-xs text-surface-600-400">{m.frameworkRefId()}</span>
							<input
								type="text"
								value={rule.ref_id}
								class="w-full text-sm border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => {
									rules[index].ref_id = e.currentTarget.value;
									persist();
								}}
							/>
						</label>
						<label class="block">
							<span class="text-xs text-surface-600-400">{m.builderLabel()}</span>
							<input
								type="text"
								value={rule.annotation}
								placeholder={m.builderLabelHint()}
								class="w-full text-sm border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => {
									rules[index].annotation = e.currentTarget.value;
									persist();
								}}
							/>
						</label>
					</div>

					<label class="block">
						<span class="text-xs text-surface-600-400">{m.builderCelExpression()}</span>
						<textarea
							value={rule.expression}
							placeholder={m.builderCelExpressionPlaceholder()}
							rows="2"
							class="w-full text-sm font-mono border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 resize-y"
							onblur={(e) => {
								rules[index].expression = e.currentTarget.value;
								persist();
							}}
						></textarea>
					</label>

					<label class="block">
						<span class="text-xs text-surface-600-400">{m.builderColor()}</span>
						<div class="flex items-center gap-2">
							<input
								type="color"
								value={rule.color ?? '#6b7280'}
								class="w-8 h-8 rounded border border-surface-200-800 cursor-pointer"
								onchange={(e) => {
									rules[index].color = e.currentTarget.value;
									persist();
								}}
							/>
							{#if rule.color}
								<button
									type="button"
									class="text-xs text-surface-500 hover:text-surface-600-400"
									onclick={() => {
										rules[index].color = null;
										persist();
									}}
								>
									{m.builderClearAction()}
								</button>
							{/if}
						</div>
					</label>

					{#if activeLanguage}
						{@const lang = activeLanguage}
						<label class="block border-t border-surface-200-800 pt-2">
							<span class="text-xs text-blue-500"
								>{m.builderCelLabelTranslate({ lang: lang.toUpperCase() })}</span
							>
							<input
								type="text"
								value={getTranslation(rule.translations, lang, 'annotation')}
								placeholder={m.builderTranslateLabel()}
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
		<p class="text-xs text-surface-500 text-center py-2">{m.builderNoOutcomeRules()}</p>
	{/if}

	<p class="text-xs text-surface-500">
		{hintParts[0] ?? ''}<code class="font-mono bg-surface-100-900 px-1 rounded">"true"</code
		>{hintParts[1] ?? ''}
	</p>

	<button
		type="button"
		class="text-xs text-surface-500 hover:text-surface-600-400"
		onclick={() => (showCelRef = !showCelRef)}
	>
		<i class="fa-solid {showCelRef ? 'fa-chevron-up' : 'fa-chevron-down'} mr-1"></i>
		{m.builderCelContextReference()}
	</button>
	{#if showCelRef}
		<div
			class="text-xs text-surface-600-400 bg-surface-50-950 border border-surface-200-800 rounded-lg p-3 font-mono space-y-3"
		>
			<div class="font-sans font-semibold text-surface-600-400">{m.builderCelGroupAssessment()}</div>
			<div class="space-y-1 ml-2">
				<div>
					<span class="text-surface-700-300">assessment.score_sum</span> — {m.builderCelScoreSum()}
				</div>
				<div>
					<span class="text-surface-700-300">assessment.score_max</span> — {m.builderCelScoreMax()}
				</div>
				<div>
					<span class="text-surface-700-300">assessment.answered_count</span> — {m.builderCelAnsweredCount()}
				</div>
				<div>
					<span class="text-surface-700-300">assessment.total_count</span> — {m.builderCelTotalCount()}
				</div>
			</div>

			<div class="font-sans font-semibold text-surface-600-400 pt-1 border-t border-surface-200-800">
				{m.builderCelGroupRequirements()}
			</div>
			<div class="space-y-1 ml-2">
				<div>
					<span class="text-surface-700-300">requirements["NODE_ID"].score</span> — {m.builderCelReqScore()}
				</div>
				<div>
					<span class="text-surface-700-300">requirements["NODE_ID"].max_score</span> —
					{m.builderCelReqMaxScore()}
				</div>
				<div>
					<span class="text-surface-700-300">requirements["NODE_ID"].result</span> —
					{m.builderCelReqResult()}
				</div>
				<div>
					<span class="text-surface-700-300">requirements["NODE_ID"].status</span> —
					{m.builderCelReqStatus()}
				</div>
				<div class="text-surface-500 italic">
					{m.builderCelNodeIdHint()}
				</div>
			</div>

			<div class="font-sans font-semibold text-surface-600-400 pt-1 border-t border-surface-200-800">
				{m.builderCelGroupAnswers()}
			</div>
			<div class="space-y-1 ml-2">
				<div>
					<span class="text-surface-700-300">answers["Q_NODE_ID"].score</span> — {m.builderCelAnswerScore()}
				</div>
				<div>
					<span class="text-surface-700-300">answers["Q_NODE_ID"].value</span> — {m.builderCelAnswerValue()}
				</div>
				<div>
					<span class="text-surface-700-300">answers["Q_NODE_ID"].selected_choices</span> —
					{m.builderCelAnswerSelectedChoices()}
				</div>
				<div>
					<span class="text-surface-700-300">answers["Q_NODE_ID"].weight</span> —
					{m.builderCelAnswerWeight()}
				</div>
				<div>
					<span class="text-surface-700-300">answers["Q_NODE_ID"].type</span> —
					{m.builderCelAnswerType()}
				</div>
			</div>

			<div class="font-sans font-semibold text-surface-600-400 pt-1 border-t border-surface-200-800">
				{m.builderCelGroupOther()}
			</div>
			<div class="space-y-1 ml-2">
				<div>
					<span class="text-surface-700-300">computed_outcomes</span> — {m.builderCelComputedOutcomes()}
				</div>
				<div>
					<span class="text-surface-700-300">hidden_requirements</span> — {m.builderCelHiddenRequirements()}
				</div>
			</div>
		</div>
	{/if}
</div>
