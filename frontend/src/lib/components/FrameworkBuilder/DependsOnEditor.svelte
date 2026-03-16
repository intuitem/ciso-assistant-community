<script lang="ts">
	import { getBuilderContext, type Question } from './builder-state';

	interface Props {
		question: Question;
		availableQuestions: Question[];
	}

	let { question, availableQuestions }: Props = $props();

	const builder = getBuilderContext();

	let active = $state(!!question.depends_on);
	let dependsOn = $state<{
		question: string;
		answers: string[];
		condition: 'any' | 'all';
	}>(
		question.depends_on
			? (question.depends_on as { question: string; answers: string[]; condition: 'any' | 'all' })
			: { question: '', answers: [], condition: 'any' }
	);

	const sourceQuestion = $derived(availableQuestions.find((q) => q.urn === dependsOn.question));

	function toggle() {
		if (active) {
			// Remove condition
			active = false;
			builder.updateQuestion(question.id, { depends_on: null });
			question.depends_on = null;
		} else {
			active = true;
		}
	}

	function save() {
		if (!dependsOn.question || dependsOn.answers.length === 0) return;
		const value = { ...dependsOn };
		builder.updateQuestion(question.id, { depends_on: value });
		question.depends_on = value;
	}

	function toggleAnswer(urn: string) {
		if (dependsOn.answers.includes(urn)) {
			dependsOn.answers = dependsOn.answers.filter((a) => a !== urn);
		} else {
			dependsOn.answers = [...dependsOn.answers, urn];
		}
		save();
	}
</script>

<div class="space-y-2">
	<button
		type="button"
		class="text-xs font-medium {active
			? 'text-amber-600'
			: 'text-gray-400 hover:text-gray-600'} transition-colors"
		onclick={toggle}
	>
		<i class="fa-solid {active ? 'fa-link-slash' : 'fa-link'} mr-1"></i>
		{active ? 'Remove condition' : 'Add condition'}
	</button>

	{#if active}
		<div class="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
			<label class="block">
				<span class="text-xs text-amber-700 font-medium">Show when this question...</span>
				<select
					value={dependsOn.question}
					class="w-full text-sm border border-amber-200 rounded px-2 py-1 mt-1 outline-none focus:border-amber-400 bg-white"
					onchange={(e) => {
						dependsOn.question = e.currentTarget.value;
						dependsOn.answers = [];
					}}
				>
					<option value="">Select a question...</option>
					{#each availableQuestions as q (q.id)}
						<option value={q.urn}>{q.ref_id || q.text || q.urn}</option>
					{/each}
				</select>
			</label>

			{#if sourceQuestion && (sourceQuestion.type === 'unique_choice' || sourceQuestion.type === 'multiple_choice')}
				<div>
					<span class="text-xs text-amber-700 font-medium">...has answer:</span>
					<div class="flex flex-wrap gap-1 mt-1">
						{#each sourceQuestion.choices as choice (choice.id)}
							{@const isSelected = dependsOn.answers.includes(choice.urn ?? '')}
							<button
								type="button"
								class="text-xs px-2 py-0.5 rounded-full border transition-colors {isSelected
									? 'bg-amber-200 border-amber-400 text-amber-800'
									: 'bg-white border-amber-200 text-amber-600 hover:border-amber-300'}"
								onclick={() => toggleAnswer(choice.urn ?? '')}
							>
								{choice.value || choice.ref_id || 'Untitled'}
							</button>
						{/each}
					</div>
				</div>

				<label class="flex items-center gap-2">
					<span class="text-xs text-amber-700 font-medium">Match:</span>
					<select
						value={dependsOn.condition}
						class="text-xs border border-amber-200 rounded px-2 py-0.5 outline-none bg-white"
						onchange={(e) => {
							dependsOn.condition = e.currentTarget.value as 'any' | 'all';
							save();
						}}
					>
						<option value="any">Any selected</option>
						<option value="all">All selected</option>
					</select>
				</label>
			{:else if sourceQuestion}
				<p class="text-xs text-amber-600">
					Conditions are only supported for choice-type questions.
				</p>
			{/if}
		</div>
	{/if}
</div>
