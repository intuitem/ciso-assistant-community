<script lang="ts">
	import { slide } from 'svelte/transition';
	import {
		getBuilderContext,
		getTranslation,
		withTranslation,
		type Question
	} from './builder-state';
	import TypeSelector from './TypeSelector.svelte';
	import ChoiceListEditor from './ChoiceListEditor.svelte';
	import DependsOnEditor from './DependsOnEditor.svelte';
	import { QUESTION_TYPES, inferVariant, defaultConfigFor } from './builder-utils.svelte';
	import ConfirmAction from './ConfirmAction.svelte';
	import * as m from '$paraglide/messages';

	interface Props {
		question: Question;
		reqNodeId: string;
		qIndex: number;
		siblingQuestions: Question[];
	}

	let { question, reqNodeId, qIndex, siblingQuestions }: Props = $props();

	const builder = getBuilderContext();
	const {
		framework: frameworkStore,
		errors: errorsStore,
		activeLanguage: activeLanguageStore
	} = builder;

	let expanded = $state(false);

	const isChoiceType = $derived(
		question.type === 'unique_choice' || question.type === 'multiple_choice'
	);

	const currentVariant = $derived(inferVariant(question));
	const variantInfo = $derived(
		QUESTION_TYPES.find((t) => t.value === currentVariant) ?? QUESTION_TYPES[0]
	);

	const sliderMin = $derived(Number((question.config as { min?: number } | null)?.min ?? 0));
	const sliderMax = $derived(Number((question.config as { max?: number } | null)?.max ?? 100));
	const sliderStep = $derived(Number((question.config as { step?: number } | null)?.step ?? 1));

	// Real-time mirror of the publish-time slider validation in `builder-state.ts`,
	// so authors see the problem while editing instead of only when they click
	// Publish. Saves still go through — blocking autosave on transient invalid
	// intermediate states would lose user input.
	const sliderConfigError = $derived.by(() => {
		if (currentVariant !== 'number:slider') return null;
		if (!(sliderMin < sliderMax)) return m.sliderMinMustBeLessThanMax();
		if (!(sliderStep > 0)) return m.sliderStepMustBeGreaterThanZero();
		if (sliderStep > sliderMax - sliderMin) return m.sliderStepCannotExceedRange();
		return null;
	});

	const dependsOnLabel = $derived.by(() => {
		if (!question.depends_on) return null;
		const dep = question.depends_on as { question: string; answers: string[] };
		const src = siblingQuestions.find((q) => q.urn === dep.question);
		if (!src) return null;
		return `Shown when ${src.ref_id || 'Q'} = ${dep.answers.length} answer(s)`;
	});

	// Available questions for depends_on: only those before this question in order
	const availableForDependsOn = $derived(
		siblingQuestions.filter((q) => q.order < question.order && q.id !== question.id)
	);

	async function saveField(field: string, value: unknown) {
		await builder.updateQuestion(question.id, { [field]: value });
	}

	async function changeVariant(newVariant: string) {
		const info = QUESTION_TYPES.find((t) => t.value === newVariant);
		if (!info) return;
		const newStoredType = info.storedType;
		if (
			isChoiceType &&
			newStoredType !== 'unique_choice' &&
			newStoredType !== 'multiple_choice' &&
			question.choices.length > 0
		) {
			if (!confirm('Changing type will delete existing choices. Continue?')) return;
		}
		await builder.updateQuestion(question.id, {
			type: newStoredType,
			config: defaultConfigFor(newVariant)
		});
	}

	function updateSliderConfig(patch: Record<string, number>) {
		const current = (question.config as Record<string, unknown> | null) ?? { widget: 'slider' };
		saveField('config', { ...current, ...patch });
	}
</script>

<div class="group flex items-start gap-1">
	<!-- Collapsed view -->
	{#if !expanded}
		<span
			class="text-gray-300 group-hover:text-gray-400 cursor-grab pt-2 pl-1"
			data-drag-handle
			aria-hidden="true"
		>
			<i class="fa-solid fa-grip-vertical text-xs"></i>
		</span>
		<button
			type="button"
			class="flex-1 flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-gray-50 transition-colors text-left"
			onclick={() => (expanded = true)}
		>
			<span class="w-6 h-6 rounded flex items-center justify-center {variantInfo.color}">
				<i class="fa-solid {variantInfo.icon} text-xs"></i>
			</span>
			<span class="flex-1 text-sm text-gray-700 truncate">
				{#if $activeLanguageStore}
					{@const translated = getTranslation(question.translations, $activeLanguageStore, 'text')}
					<span class="text-gray-400">{question.text || 'Untitled'}</span>
					{#if translated}
						<span class="text-blue-600 ml-1">| {translated}</span>
					{:else}
						<span class="text-amber-500 ml-1" title="Not translated">*</span>
					{/if}
				{:else}
					{question.text || 'Untitled question'}
				{/if}
			</span>
			{#if dependsOnLabel}
				<span class="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
					<i class="fa-solid fa-link text-[10px] mr-0.5"></i>
					{dependsOnLabel}
				</span>
			{/if}
			<span class="text-xs font-medium px-2 py-0.5 rounded {variantInfo.color}">
				{variantInfo.label}
			</span>
		</button>
	{/if}

	<!-- Expanded view -->
	{#if expanded}
		<span
			class="text-gray-300 group-hover:text-gray-400 cursor-grab pt-5 pl-1"
			data-drag-handle
			aria-hidden="true"
		>
			<i class="fa-solid fa-grip-vertical text-xs"></i>
		</span>
		<div
			transition:slide={{ duration: 200 }}
			class="flex-1 border border-gray-200 rounded-lg p-4 space-y-3 bg-white"
		>
			<div class="flex items-center justify-between">
				<TypeSelector {currentVariant} onselect={changeVariant} />
				<div class="flex items-center gap-2">
					<ConfirmAction
						message="Delete this question?"
						onconfirm={() => builder.deleteQuestion(reqNodeId, qIndex)}
						confirmLabel="Yes"
						triggerClass="text-gray-300 hover:text-red-500 transition-colors"
						confirmClass="text-xs text-red-600 font-medium px-2 py-0.5 rounded bg-red-50 hover:bg-red-100"
					/>
					<button
						type="button"
						class="text-gray-400 hover:text-gray-600"
						onclick={() => (expanded = false)}
					>
						<i class="fa-solid fa-chevron-up text-xs"></i>
					</button>
				</div>
			</div>

			{#if currentVariant === 'number:slider'}
				<div class="grid grid-cols-3 gap-2">
					<label class="block">
						<span class="text-xs text-gray-500">{m.sliderMin()}</span>
						<input
							type="number"
							value={sliderMin}
							class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/40"
							onblur={(e) => updateSliderConfig({ min: Number(e.currentTarget.value) })}
						/>
					</label>
					<label class="block">
						<span class="text-xs text-gray-500">{m.sliderMax()}</span>
						<input
							type="number"
							value={sliderMax}
							class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/40"
							onblur={(e) => updateSliderConfig({ max: Number(e.currentTarget.value) })}
						/>
					</label>
					<label class="block">
						<span class="text-xs text-gray-500">{m.sliderStep()}</span>
						<input
							type="number"
							value={sliderStep}
							min="0"
							class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/40"
							onblur={(e) => updateSliderConfig({ step: Number(e.currentTarget.value) })}
						/>
					</label>
				</div>
			{/if}

			{#if sliderConfigError}
				<p class="text-xs text-amber-600">
					<i class="fa-solid fa-triangle-exclamation mr-1"></i>
					{sliderConfigError}
				</p>
			{/if}

			{#if currentVariant === 'unique_choice:slider' && question.choices.length < 2}
				<p class="text-xs text-amber-600">
					<i class="fa-solid fa-triangle-exclamation mr-1"></i>
					{m.sliderNeedsAtLeastTwoChoices()}
				</p>
			{/if}

			<!-- Question text -->
			{#if $activeLanguageStore}
				{@const lang = $activeLanguageStore}
				<div class="grid grid-cols-2 gap-3">
					<textarea
						value={question.text ?? ''}
						readonly
						rows="2"
						class="w-full text-sm border border-gray-100 rounded-lg px-3 py-2 resize-none text-gray-400 bg-gray-50 cursor-default"
					></textarea>
					<textarea
						value={getTranslation(question.translations, lang, 'text')}
						placeholder="Translate question..."
						rows="2"
						class="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 resize-none"
						onblur={(e) => {
							saveField(
								'translations',
								withTranslation(question.translations, lang, 'text', e.currentTarget.value)
							);
						}}
					></textarea>
				</div>
			{:else}
				<textarea
					value={question.text ?? ''}
					placeholder="Enter your question..."
					rows="2"
					class="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 resize-none"
					onblur={(e) => {
						saveField('text', e.currentTarget.value);
					}}
				></textarea>
			{/if}

			<!-- Metadata row -->
			<div class="grid grid-cols-3 gap-2">
				<label class="block">
					<span class="text-xs text-gray-500">Ref ID</span>
					<input
						type="text"
						value={question.ref_id ?? ''}
						class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/40"
						onblur={(e) => {
							saveField('ref_id', e.currentTarget.value || null);
						}}
					/>
				</label>
				<label class="block">
					<span class="text-xs text-gray-500">Weight</span>
					<input
						type="number"
						value={question.weight}
						min="0"
						class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/40"
						onblur={(e) => {
							const val = Number(e.currentTarget.value) || 1;
							saveField('weight', val);
						}}
					/>
				</label>
				<label class="block">
					<span class="text-xs text-gray-500">Annotation</span>
					<input
						type="text"
						value={question.annotation ?? ''}
						placeholder="Optional note..."
						class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/40"
						onblur={(e) => {
							saveField('annotation', e.currentTarget.value || null);
						}}
					/>
				</label>
			</div>

			<!-- Choice list for choice types -->
			{#if isChoiceType}
				<ChoiceListEditor
					choices={question.choices}
					{reqNodeId}
					{qIndex}
					implementationGroups={$frameworkStore.implementation_groups_definition}
					minScore={$frameworkStore.min_score}
					maxScore={$frameworkStore.max_score}
				/>
			{/if}

			<!-- Depends on -->
			<DependsOnEditor {question} availableQuestions={availableForDependsOn} />

			{#if $errorsStore.has(`question-${question.id}`)}
				<p class="text-xs text-red-600">
					{$errorsStore.get(`question-${question.id}`)}
				</p>
			{/if}
		</div>
	{/if}
</div>
