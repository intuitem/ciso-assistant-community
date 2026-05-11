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
	import { TYPE_ICONS, TYPE_COLORS } from './builder-utils.svelte';
	import ConfirmAction from './ConfirmAction.svelte';

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

	const supportsSlider = $derived(question.type === 'number' || question.type === 'unique_choice');

	const sliderEnabled = $derived(
		(question.config as { widget?: string } | null)?.widget === 'slider'
	);

	const sliderMin = $derived(Number((question.config as { min?: number } | null)?.min ?? 0));
	const sliderMax = $derived(Number((question.config as { max?: number } | null)?.max ?? 100));
	const sliderStep = $derived(Number((question.config as { step?: number } | null)?.step ?? 1));

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

	async function changeType(newType: string) {
		if (
			isChoiceType &&
			newType !== 'unique_choice' &&
			newType !== 'multiple_choice' &&
			question.choices.length > 0
		) {
			if (!confirm('Changing type will delete existing choices. Continue?')) return;
		}
		// Slider config is tied to the data shape — wipe it on any type change.
		await builder.updateQuestion(question.id, { type: newType, config: null });
	}

	function enableSlider() {
		const config =
			question.type === 'number'
				? { widget: 'slider', min: 0, max: 100, step: 1 }
				: { widget: 'slider' };
		saveField('config', config);
	}

	function disableSlider() {
		saveField('config', null);
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
			<span
				class="w-6 h-6 rounded flex items-center justify-center {TYPE_COLORS[question.type] ??
					'text-gray-400 bg-gray-100'}"
			>
				<i class="fa-solid {TYPE_ICONS[question.type] ?? 'fa-question'} text-xs"></i>
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
			<span
				class="text-xs font-medium px-2 py-0.5 rounded {TYPE_COLORS[question.type] ??
					'text-gray-400 bg-gray-100'}"
			>
				{question.type.replace('_', ' ')}
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
				<TypeSelector currentType={question.type} onselect={changeType} />
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

			{#if supportsSlider}
				<div class="flex items-center gap-2 text-xs text-gray-600">
					<span class="font-medium">Widget:</span>
					<div class="inline-flex rounded border border-gray-200 overflow-hidden">
						<button
							type="button"
							class="px-2 py-0.5 transition-colors {!sliderEnabled
								? 'bg-blue-500 text-white'
								: 'bg-white text-gray-600 hover:bg-gray-50'}"
							onclick={() => {
								if (sliderEnabled) disableSlider();
							}}
						>
							Input
						</button>
						<button
							type="button"
							class="px-2 py-0.5 transition-colors {sliderEnabled
								? 'bg-blue-500 text-white'
								: 'bg-white text-gray-600 hover:bg-gray-50'}"
							onclick={() => {
								if (!sliderEnabled) enableSlider();
							}}
						>
							Slider
						</button>
					</div>
				</div>

				{#if sliderEnabled && question.type === 'number'}
					<div class="grid grid-cols-3 gap-2">
						<label class="block">
							<span class="text-xs text-gray-500">Min</span>
							<input
								type="number"
								value={sliderMin}
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => updateSliderConfig({ min: Number(e.currentTarget.value) })}
							/>
						</label>
						<label class="block">
							<span class="text-xs text-gray-500">Max</span>
							<input
								type="number"
								value={sliderMax}
								class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/40"
								onblur={(e) => updateSliderConfig({ max: Number(e.currentTarget.value) })}
							/>
						</label>
						<label class="block">
							<span class="text-xs text-gray-500">Step</span>
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

				{#if sliderEnabled && question.type === 'unique_choice' && question.choices.length < 2}
					<p class="text-xs text-amber-600">
						<i class="fa-solid fa-triangle-exclamation mr-1"></i>
						Slider needs at least 2 choices.
					</p>
				{/if}
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
