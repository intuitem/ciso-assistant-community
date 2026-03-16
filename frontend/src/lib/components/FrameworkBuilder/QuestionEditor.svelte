<script lang="ts">
	import { slide } from 'svelte/transition';
	import { getBuilderContext, type Question } from './builder-state';
	import TypeSelector from './TypeSelector.svelte';
	import ChoiceListEditor from './ChoiceListEditor.svelte';
	import DependsOnEditor from './DependsOnEditor.svelte';

	interface Props {
		question: Question;
		sectionIndex: number;
		reqIndex: number;
		qIndex: number;
		siblingQuestions: Question[];
	}

	let { question, sectionIndex, reqIndex, qIndex, siblingQuestions }: Props = $props();

	const builder = getBuilderContext();
	const { framework: frameworkStore, errors: errorsStore } = builder;

	let expanded = $state(false);
	let confirmDelete = $state(false);

	const typeIcons: Record<string, string> = {
		text: 'fa-font',
		number: 'fa-hashtag',
		boolean: 'fa-toggle-on',
		unique_choice: 'fa-circle-dot',
		multiple_choice: 'fa-square-check',
		date: 'fa-calendar'
	};

	const typeColors: Record<string, string> = {
		text: 'text-blue-600 bg-blue-50',
		number: 'text-emerald-600 bg-emerald-50',
		boolean: 'text-green-600 bg-green-50',
		unique_choice: 'text-violet-600 bg-violet-50',
		multiple_choice: 'text-purple-600 bg-purple-50',
		date: 'text-amber-600 bg-amber-50'
	};

	const isChoiceType = $derived(
		question.type === 'unique_choice' || question.type === 'multiple_choice'
	);

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
		await saveField('type', newType);
	}
</script>

<div class="group">
	<!-- Collapsed view -->
	{#if !expanded}
		<button
			type="button"
			class="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors text-left"
			onclick={() => (expanded = true)}
		>
			<span class="text-gray-300 group-hover:text-gray-400 cursor-grab">
				<i class="fa-solid fa-grip-vertical text-xs"></i>
			</span>
			<span
				class="w-6 h-6 rounded flex items-center justify-center {typeColors[question.type] ??
					'text-gray-400 bg-gray-100'}"
			>
				<i class="fa-solid {typeIcons[question.type] ?? 'fa-question'} text-xs"></i>
			</span>
			<span class="flex-1 text-sm text-gray-700 truncate">
				{question.text || 'Untitled question'}
			</span>
			{#if dependsOnLabel}
				<span class="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
					<i class="fa-solid fa-link text-[10px] mr-0.5"></i>
					{dependsOnLabel}
				</span>
			{/if}
			<span
				class="text-xs font-medium px-2 py-0.5 rounded {typeColors[question.type] ??
					'text-gray-400 bg-gray-100'}"
			>
				{question.type.replace('_', ' ')}
			</span>
		</button>
	{/if}

	<!-- Expanded view -->
	{#if expanded}
		<div
			transition:slide={{ duration: 200 }}
			class="border border-gray-200 rounded-lg p-4 space-y-3 bg-white"
		>
			<div class="flex items-center justify-between">
				<TypeSelector currentType={question.type} onselect={changeType} />
				<div class="flex items-center gap-2">
					{#if confirmDelete}
						<span class="text-xs text-red-600 font-medium">Delete this question?</span>
						<button
							type="button"
							class="text-xs text-red-600 font-medium px-2 py-0.5 rounded bg-red-50 hover:bg-red-100"
							onclick={() => {
								builder.deleteQuestion(sectionIndex, reqIndex, qIndex);
								confirmDelete = false;
							}}
						>
							Yes
						</button>
						<button
							type="button"
							class="text-xs text-gray-500 px-2 py-0.5"
							onclick={() => (confirmDelete = false)}
						>
							No
						</button>
					{:else}
						<button
							type="button"
							class="text-gray-300 hover:text-red-500 transition-colors"
							onclick={() => (confirmDelete = true)}
						>
							<i class="fa-solid fa-trash text-xs"></i>
						</button>
					{/if}
					<button
						type="button"
						class="text-gray-400 hover:text-gray-600"
						onclick={() => (expanded = false)}
					>
						<i class="fa-solid fa-chevron-up text-xs"></i>
					</button>
				</div>
			</div>

			<!-- Question text -->
			<textarea
				value={question.text ?? ''}
				placeholder="Enter your question..."
				rows="2"
				class="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:border-blue-500 outline-none resize-none"
				onblur={(e) => {
					saveField('text', e.currentTarget.value);
				}}
			></textarea>

			<!-- Metadata row -->
			<div class="grid grid-cols-3 gap-2">
				<label class="block">
					<span class="text-xs text-gray-500">Ref ID</span>
					<input
						type="text"
						value={question.ref_id ?? ''}
						class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none"
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
						class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none"
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
						class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none"
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
					{sectionIndex}
					{reqIndex}
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
