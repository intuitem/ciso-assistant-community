<script lang="ts">
	import { getBuilderContext, type BuilderRequirement } from './builder-state.svelte';
	import QuestionEditor from './QuestionEditor.svelte';

	interface Props {
		requirement: BuilderRequirement;
		sectionIndex: number;
		reqIndex: number;
	}

	let { requirement, sectionIndex, reqIndex }: Props = $props();

	const state = getBuilderContext();
	let confirmDelete = $state(false);

	const igDef = $derived(state.framework.implementation_groups_definition);

	async function saveField(field: string, value: unknown) {
		(requirement.node as Record<string, unknown>)[field] = value;
		await state.updateNode(requirement.node.id, { [field]: value });
	}

	// All questions in this requirement (for depends_on editor)
	const allQuestions = $derived(requirement.questions.map((q) => q.question));
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-gray-100 flex items-start gap-3 group">
		<span class="cursor-grab text-gray-300 group-hover:text-gray-400 mt-1">
			<i class="fa-solid fa-grip-vertical text-xs"></i>
		</span>
		<div class="flex-1 min-w-0 space-y-1">
			<div class="flex items-center gap-2">
				<input
					type="text"
					value={requirement.node.ref_id ?? ''}
					placeholder="Ref ID"
					class="w-24 text-xs font-mono bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none transition-colors text-gray-500"
					onblur={(e) => saveField('ref_id', e.currentTarget.value || null)}
				/>
				<input
					type="text"
					value={requirement.node.name ?? ''}
					placeholder="Requirement name"
					class="flex-1 text-sm font-medium bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none transition-colors"
					onblur={(e) => saveField('name', e.currentTarget.value || null)}
				/>
			</div>
			<textarea
				value={requirement.node.description ?? ''}
				placeholder="Description (optional)"
				rows="1"
				class="w-full text-xs text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none transition-colors resize-none"
				onblur={(e) => saveField('description', e.currentTarget.value || null)}
			></textarea>
		</div>

		<div class="flex items-center gap-1 shrink-0">
			{#if confirmDelete}
				<button
					type="button"
					class="text-xs text-red-600 font-medium px-2 py-0.5 rounded bg-red-50"
					onclick={() => {
						state.deleteRequirement(sectionIndex, reqIndex);
						confirmDelete = false;
					}}
				>
					Delete
				</button>
				<button
					type="button"
					class="text-xs text-gray-500 px-2 py-0.5"
					onclick={() => (confirmDelete = false)}
				>
					Cancel
				</button>
			{:else}
				<button
					type="button"
					class="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 transition-all"
					onclick={() => (confirmDelete = true)}
				>
					<i class="fa-solid fa-trash text-xs"></i>
				</button>
			{/if}
		</div>
	</div>

	<!-- Implementation groups -->
	{#if igDef && igDef.length > 0}
		<div class="px-4 py-2 border-b border-gray-100">
			<span class="text-xs text-gray-500 mr-2">Groups:</span>
			{#each igDef as ig}
				{@const refId = (ig as Record<string, string>).ref_id}
				{@const selected = (requirement.node.implementation_groups ?? []).includes(refId)}
				<button
					type="button"
					class="text-xs px-2 py-0.5 rounded-full border mr-1 transition-colors {selected
						? 'bg-blue-100 border-blue-300 text-blue-700'
						: 'bg-gray-50 border-gray-200 text-gray-400 hover:border-gray-300'}"
					onclick={() => {
						const current = requirement.node.implementation_groups ?? [];
						const next = selected
							? current.filter((g: string) => g !== refId)
							: [...current, refId];
						requirement.node.implementation_groups = next;
						state.updateNode(requirement.node.id, { implementation_groups: next });
					}}
				>
					{refId}
				</button>
			{/each}
		</div>
	{/if}

	<!-- Questions -->
	<div class="px-4 py-3 space-y-1">
		{#each requirement.questions as bq, qIndex (bq.question.id)}
			<QuestionEditor
				question={bq.question}
				{sectionIndex}
				{reqIndex}
				{qIndex}
				siblingQuestions={allQuestions}
			/>
		{/each}

		<button
			type="button"
			class="w-full py-2 border-2 border-dashed border-gray-200 rounded-lg text-xs text-gray-400 hover:text-gray-600 hover:border-gray-300 transition-colors"
			onclick={() => state.addQuestion(sectionIndex, reqIndex)}
		>
			<i class="fa-solid fa-plus mr-1"></i>Add question
		</button>
	</div>

	{#if state.errors.has(`node-${requirement.node.id}`)}
		<div class="px-4 py-2 bg-red-50 border-t border-red-200">
			<p class="text-xs text-red-600">{state.errors.get(`node-${requirement.node.id}`)}</p>
		</div>
	{/if}
</div>
