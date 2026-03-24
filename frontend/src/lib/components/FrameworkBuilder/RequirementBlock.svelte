<script lang="ts">
	import { getBuilderContext, type BuilderRequirement } from './builder-state';
	import QuestionEditor from './QuestionEditor.svelte';

	interface Props {
		requirement: BuilderRequirement;
	}

	let { requirement }: Props = $props();

	const builder = getBuilderContext();
	const { framework: frameworkStore, errors: errorsStore } = builder;
	let confirmDelete = $state(false);
	let urnCopied = $state(false);

	const depthColors = [
		'border-l-blue-400',
		'border-l-violet-400',
		'border-l-amber-400',
		'border-l-emerald-400'
	];
	const depthColor = $derived(depthColors[requirement.depth % depthColors.length]);

	async function saveField(field: string, value: unknown) {
		await builder.updateNode(requirement.node.id, { [field]: value });
	}

	const allQuestions = $derived(requirement.questions.map((q) => q.question));

	// Drag state for children
	let draggedChildIndex: number | null = $state(null);

	function handleChildDragStart(e: DragEvent, index: number) {
		const target = e.target as HTMLElement;
		if (!target.closest('[data-drag-handle]')) {
			e.preventDefault();
			return;
		}
		draggedChildIndex = index;
	}
	function handleChildDragOver(e: DragEvent) {
		e.preventDefault();
	}
	function handleChildDrop(e: DragEvent, dropIndex: number) {
		e.preventDefault();
		if (draggedChildIndex === null || draggedChildIndex === dropIndex) return;
		builder.reorderRequirements(requirement.node.id, draggedChildIndex, dropIndex);
		draggedChildIndex = null;
	}
	function handleChildDragEnd() {
		draggedChildIndex = null;
	}
</script>

<div style="margin-left: {Math.min(requirement.depth, 3) * 16}px">
	<div
		class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden {requirement.depth >
		0
			? `border-l-4 ${depthColor}`
			: ''}"
	>
		<!-- Parent breadcrumb for deep nesting -->
		{#if requirement.depth >= 3 && requirement.node.parent_urn}
			<div class="px-4 pt-2 pb-0">
				<span class="text-[10px] text-gray-400">
					<i class="fa-solid fa-turn-up fa-rotate-90 mr-1"></i>nested under {requirement.node.parent_urn
						.split(':')
						.pop()
						?.slice(0, 12)}
				</span>
			</div>
		{/if}

		<!-- Header -->
		<div class="px-4 py-3 border-b border-gray-100 flex items-start gap-3 group">
			<span class="cursor-grab text-gray-300 group-hover:text-gray-400 mt-1" data-drag-handle>
				<i class="fa-solid fa-grip-vertical text-xs"></i>
			</span>
			<div class="flex-1 min-w-0 space-y-1">
				<div class="flex items-center gap-2">
					<input
						type="text"
						value={requirement.node.ref_id ?? ''}
						placeholder="Ref ID"
						class="w-24 text-xs font-mono bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors text-gray-500"
						onblur={(e) => saveField('ref_id', e.currentTarget.value || null)}
					/>
					<input
						type="text"
						value={requirement.node.name ?? ''}
						placeholder={requirement.node.description
							? requirement.node.description.slice(0, 60) +
								(requirement.node.description.length > 60 ? '...' : '')
							: 'Requirement name'}
						class="flex-1 text-sm font-medium bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors"
						onblur={(e) => saveField('name', e.currentTarget.value || null)}
					/>
				</div>
				{#if requirement.node.urn}
					<button
						type="button"
						class="inline-flex items-center gap-1 text-[10px] font-mono text-gray-300 hover:text-gray-500 transition-colors truncate max-w-full text-left group/urn"
						onclick={() => {
							navigator.clipboard.writeText(requirement.node.urn ?? '');
							urnCopied = true;
							setTimeout(() => (urnCopied = false), 1500);
						}}
					>
						<i class="fa-solid {urnCopied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"></i>
						{#if urnCopied}
							<span class="text-green-500">Copied!</span>
						{:else}
							{requirement.node.urn}
						{/if}
					</button>
				{/if}
				<textarea
					value={requirement.node.description ?? ''}
					placeholder="Description (optional)"
					rows="1"
					class="w-full text-xs text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
					onblur={(e) => saveField('description', e.currentTarget.value || null)}
				></textarea>
			</div>

			<div class="flex items-center gap-1 shrink-0">
				{#if confirmDelete}
					<button
						type="button"
						class="text-xs text-red-600 font-medium px-2 py-0.5 rounded bg-red-50"
						onclick={() => {
							builder.deleteRequirement(requirement.node.id);
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
		{#if $frameworkStore.implementation_groups_definition && $frameworkStore.implementation_groups_definition.length > 0}
			<div class="px-4 py-2 border-b border-gray-100">
				<span class="text-xs text-gray-500 mr-2">Implementation groups:</span>
				{#each $frameworkStore.implementation_groups_definition as ig}
					{@const refId = (ig as Record<string, string>).ref_id}
					{@const selected = (requirement.node.implementation_groups ?? []).includes(refId)}
					<button
						type="button"
						class="text-xs px-2 py-0.5 rounded-full border mr-1 transition-colors {selected
							? 'bg-blue-100 border-blue-300 text-blue-700'
							: 'bg-gray-50 border-gray-200 text-gray-400 hover:border-gray-300'}"
						onclick={() => {
							const current = requirement.node.implementation_groups ?? [];
							const next = selected ? current.filter((g) => g !== refId) : [...current, refId];
							builder.updateNode(requirement.node.id, { implementation_groups: next });
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
					reqNodeId={requirement.node.id}
					{qIndex}
					siblingQuestions={allQuestions}
				/>
			{/each}

			<button
				type="button"
				class="w-full py-2 border-2 border-dashed border-gray-200 rounded-lg text-xs text-gray-400 hover:text-gray-600 hover:border-gray-300 transition-colors"
				onclick={() => builder.addQuestion(requirement.node.id)}
			>
				<i class="fa-solid fa-plus mr-1"></i>Add question
			</button>
			{#if requirement.node.urn}
				<button
					type="button"
					class="w-full py-1 text-[11px] text-gray-300 hover:text-gray-500 transition-colors"
					onclick={() => builder.addRequirement(requirement.node.id, requirement.node.urn ?? '')}
				>
					<i class="fa-solid fa-plus mr-1"></i>Add sub-requirement
				</button>
			{/if}
		</div>

		{#if $errorsStore.has(`node-${requirement.node.id}`)}
			<div class="px-4 py-2 bg-red-50 border-t border-red-200">
				<p class="text-xs text-red-600">{$errorsStore.get(`node-${requirement.node.id}`)}</p>
			</div>
		{/if}
	</div>

	<!-- Children rendered as siblings (outside card) to avoid compound padding -->
	{#if requirement.children.length > 0}
		<div class="space-y-3 mt-2">
			{#each requirement.children as child, childIndex (child.node.id)}
				<div
					class:opacity-50={draggedChildIndex === childIndex}
					draggable="true"
					ondragstart={(e) => handleChildDragStart(e, childIndex)}
					ondragover={handleChildDragOver}
					ondrop={(e) => handleChildDrop(e, childIndex)}
					ondragend={handleChildDragEnd}
					role="listitem"
				>
					<svelte:self requirement={child} />
				</div>
			{/each}
		</div>
	{/if}
</div>
