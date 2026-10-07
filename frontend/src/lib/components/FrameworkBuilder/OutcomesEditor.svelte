<script lang="ts">
	import { getTranslation, withTranslation, type OutcomeRule } from './builder-state';
	import { createHandleGatedDragHandlers } from './builder-utils.svelte';
	import ConfirmAction from './ConfirmAction.svelte';
	import CelInput from './CelInput.svelte';
	import { SECTION_ICON, SECTION_TITLE } from './section-style';
	import { readableValues, type CelCatalog } from './cel-complete';
	import { m } from '$paraglide/messages';

	interface Props {
		outcomes: OutcomeRule[];
		onupdate: (rules: OutcomeRule[]) => void;
		activeLanguage?: string | null;
		/** Which evaluator the rules will run against — the two expose different
		 * context roots, and a rule written for the wrong one silently never fires. */
		mode?: 'framework' | 'quick_form';
		/** Quick forms: pages a number rule can read the score of. */
		pages?: { id: string; label: string }[];
		/** What the expression field suggests. */
		catalog?: CelCatalog;
	}

	let {
		outcomes,
		onupdate,
		activeLanguage = null,
		mode = 'framework',
		pages = [],
		catalog = { mode: 'framework', nodes: [], questions: [] }
	}: Props = $props();

	// The picker writes, and only ever replaces, a bare page score: a hand-written
	// expression is never overwritten by it.
	const PAGE_SCORE = /^\s*pages\["([^"]+)"\]\.score\s*$/;
	const pageScoreOf = (expression: string | undefined) =>
		expression ? (PAGE_SCORE.exec(expression)?.[1] ?? null) : null;
	const pagePickable = (expression: string | undefined) =>
		!expression?.trim() || pageScoreOf(expression) !== null;

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

	const drag = createHandleGatedDragHandlers((from, to) => {
		const copy = [...rules];
		const [moved] = copy.splice(from, 1);
		copy.splice(to, 0, moved);
		rules = copy;
		persist();
	});

	const CEL_REFERENCE = $derived(
		mode === 'quick_form'
			? [
					{
						title: m.builderCelGroupResponse(),
						rows: [
							['response.score', m.builderCelResponseScore()],
							['response.score_sum', m.builderCelScoreSum()],
							['response.score_max', m.builderCelScoreMax()],
							['response.answered_count', m.builderCelAnsweredQuestions()],
							['response.total_count', m.builderCelTotalQuestions()],
							['response.complete', m.builderCelResponseComplete()]
						]
					},
					{
						title: m.builderCelGroupPages(),
						rows: [
							['pages["PAGE_ID"].visible', m.builderCelPageVisible()],
							['pages["PAGE_ID"].score', m.builderCelPageScore()],
							['pages["PAGE_ID"].score_max', m.builderCelPageScoreMax()],
							['pages["PAGE_ID"].answered_count', m.builderCelAnsweredQuestions()],
							['pages["PAGE_ID"].total_count', m.builderCelTotalQuestions()]
						],
						hint: m.builderCelNodeIdHintQuickForm()
					},
					{
						title: m.builderCelGroupAnswers(),
						rows: [
							['answers["Q_NODE_ID"].value', m.builderCelAnswerValue()],
							['answers["Q_NODE_ID"].score', m.builderCelAnswerScore()],
							['answers["Q_NODE_ID"].selected_choices', m.builderCelAnswerSelectedChoices()],
							['answers["Q_NODE_ID"].weight', m.builderCelAnswerWeight()],
							['answers["Q_NODE_ID"].type', m.builderCelAnswerType()],
							['answers["Q_NODE_ID"].answered', m.builderCelAnswerAnswered()]
						]
					},
					{
						title: m.builderCelGroupOther(),
						rows: [
							['values.REF_ID', m.builderCelValues()],
							['computed_outcomes', m.builderCelComputedOutcomes()],
							['hidden_pages', m.builderCelHiddenPages()]
						]
					}
				]
			: [
					{
						title: m.builderCelGroupAssessment(),
						rows: [
							['assessment.score_sum', m.builderCelScoreSum()],
							['assessment.score_max', m.builderCelScoreMax()],
							['assessment.answered_count', m.builderCelAnsweredCount()],
							['assessment.total_count', m.builderCelTotalCount()]
						]
					},
					{
						title: m.builderCelGroupRequirements(),
						rows: [
							['requirements["NODE_ID"].score', m.builderCelReqScore()],
							['requirements["NODE_ID"].max_score', m.builderCelReqMaxScore()],
							['requirements["NODE_ID"].result', m.builderCelReqResult()],
							['requirements["NODE_ID"].status', m.builderCelReqStatus()]
						],
						hint: m.builderCelNodeIdHint()
					},
					{
						title: m.builderCelGroupAnswers(),
						rows: [
							['answers["Q_NODE_ID"].score', m.builderCelAnswerScore()],
							['answers["Q_NODE_ID"].value', m.builderCelAnswerValue()],
							['answers["Q_NODE_ID"].selected_choices', m.builderCelAnswerSelectedChoices()],
							['answers["Q_NODE_ID"].weight', m.builderCelAnswerWeight()],
							['answers["Q_NODE_ID"].type', m.builderCelAnswerType()]
						]
					},
					{
						title: m.builderCelGroupOther(),
						rows: [
							['computed_outcomes', m.builderCelComputedOutcomes()],
							['hidden_requirements', m.builderCelHiddenRequirements()]
						]
					}
				]
	);

	// Split the hint message around its {trueLiteral} placeholder so we can render
	// a real <code> element in the middle without resorting to {@html}. The NUL
	// sentinel is safe because translations are baked at build time.
	const hintParts = $derived(m.builderOutcomeRulesHint({ trueLiteral: '\x00' }).split('\x00'));
</script>

<div class="space-y-1.5">
	<div class="flex items-center justify-between">
		<span class={SECTION_TITLE}
			><i class="{SECTION_ICON} fa-code-branch" aria-hidden="true"
			></i>{m.builderOutcomeRules()}</span
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
			onmousedown={drag.recordMousedown}
			ondragstart={(e) => drag.handleDragStart(e, index)}
			ondragover={drag.handleDragOver}
			ondrop={(e) => drag.handleDrop(e, index)}
			ondragend={drag.handleDragEnd}
			role="listitem"
		>
			<!-- Collapsed row -->
			<div class="flex items-center gap-2 px-3 py-2">
				<span class="cursor-grab text-gray-300 hover:text-surface-600-400" data-drag-handle>
					<i class="fa-solid fa-grip-vertical text-xs"></i>
				</span>

				{#if rule.kind === 'number'}
					<span
						class="text-[10px] font-mono font-semibold px-1 rounded bg-surface-200-800 text-surface-600-400"
						title={m.builderRuleKindNumber()}>#</span
					>
				{:else if rule.color}
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
								class="input w-full text-sm border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
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
								class="input w-full text-sm border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => {
									rules[index].annotation = e.currentTarget.value;
									persist();
								}}
							/>
						</label>
					</div>

					{#if mode === 'quick_form'}
						<label class="block">
							<span class="text-xs text-surface-600-400">{m.builderRuleKind()}</span>
							<select
								class="w-full text-sm border border-surface-200-800 rounded px-2 py-1 bg-surface-50-950"
								value={rule.kind === 'number' ? 'number' : 'boolean'}
								onchange={(e) => {
									if (e.currentTarget.value === 'number') {
										rules[index].kind = 'number';
										rules[index].color = null;
									} else {
										delete rules[index].kind;
									}
									persist();
								}}
								data-testid="outcome-rule-kind"
							>
								<option value="boolean">{m.builderRuleKindBoolean()}</option>
								<option value="number">{m.builderRuleKindNumber()}</option>
							</select>
							<span class="text-xs text-surface-500">{m.builderRuleKindHint()}</span>
						</label>
					{/if}

					<div class="block">
						<span class="text-xs text-surface-600-400">{m.builderCelExpression()}</span>
						<CelInput
							multiline
							value={rule.expression}
							placeholder={mode === 'quick_form'
								? m.builderCelExpressionPlaceholderQuickForm()
								: m.builderCelExpressionPlaceholder()}
							class="input w-full text-sm font-mono border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 resize-y"
							{catalog}
							place={{ where: 'outcome', values: readableValues(rules, index) }}
							oncommit={(value) => {
								rules[index].expression = value;
								persist();
							}}
							testid="outcome-rule-expression"
						/>
					</div>

					{#if mode === 'quick_form' && rule.kind === 'number' && pages.length && pagePickable(rule.expression)}
						<label class="block">
							<span class="text-xs text-surface-600-400">{m.builderUsePageScore()}</span>
							<select
								class="w-full text-sm border border-surface-200-800 rounded px-2 py-1 bg-surface-50-950"
								value={pageScoreOf(rule.expression) ?? ''}
								onchange={(e) => {
									const id = e.currentTarget.value;
									rules[index].expression = id ? `pages["${id}"].score` : '';
									persist();
								}}
								data-testid="outcome-rule-page-score"
							>
								<option value="">--</option>
								{#each pages as page (page.id)}
									<option value={page.id}>{page.label || page.id}</option>
								{/each}
							</select>
							<span class="text-xs text-surface-500">{m.builderUsePageScoreHint()}</span>
						</label>
					{/if}

					{#if rule.kind !== 'number'}
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
					{/if}

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
								class="input w-full text-sm border border-blue-100 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
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
			{#each CEL_REFERENCE as group, gi (group.title)}
				<div
					class="font-sans font-semibold text-surface-600-400 {gi > 0
						? 'pt-1 border-t border-surface-200-800'
						: ''}"
				>
					{group.title}
				</div>
				<div class="space-y-1 ml-2">
					{#each group.rows as [expr, description] (expr)}
						<div><span class="text-surface-700-300">{expr}</span> — {description}</div>
					{/each}
					{#if group.hint}
						<div class="text-surface-500 italic">{group.hint}</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
