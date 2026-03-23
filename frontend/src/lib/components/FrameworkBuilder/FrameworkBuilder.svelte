<script lang="ts">
	import { onMount } from 'svelte';
	import {
		createBuilderState,
		setBuilderContext,
		type Framework,
		type RequirementNode,
		type Question
	} from './builder-state';
	import { initBuilderApi } from './builder-api';
	import BuilderMinimap from './BuilderMinimap.svelte';
	import SectionBlock from './SectionBlock.svelte';
	import OutcomesEditor from './OutcomesEditor.svelte';

	interface Props {
		framework: Framework;
		requirementNodes: RequirementNode[];
		questions: Question[];
	}

	let { framework, requirementNodes, questions }: Props = $props();

	initBuilderApi(fetch, framework.id);

	const builder = createBuilderState(framework, requirementNodes, questions);
	setBuilderContext(builder);

	const {
		framework: frameworkStore,
		sections: sectionsStore,
		errors: errorsStore,
		saving: savingStore
	} = builder;

	let urnCopied = $state(false);

	// Drag state for sections
	let draggedSectionIndex: number | null = $state(null);

	function handleSectionDragStart(index: number) {
		draggedSectionIndex = index;
	}

	function handleSectionDragOver(e: DragEvent) {
		e.preventDefault();
	}

	function handleSectionDrop(e: DragEvent, dropIndex: number) {
		e.preventDefault();
		if (draggedSectionIndex === null || draggedSectionIndex === dropIndex) return;
		builder.reorderSections(draggedSectionIndex, dropIndex);
		draggedSectionIndex = null;
	}

	function handleSectionDragEnd() {
		draggedSectionIndex = null;
	}

	// IntersectionObserver for minimap active section
	onMount(() => {
		const observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (entry.isIntersecting) {
						const id = (entry.target as HTMLElement).dataset.sectionId;
						if (id) builder.activeSection.set(id);
					}
				}
			},
			{ rootMargin: '-80px 0px -60% 0px', threshold: 0 }
		);

		const elements = document.querySelectorAll('[data-section-id]');
		elements.forEach((el) => observer.observe(el));

		return () => observer.disconnect();
	});
</script>

<div class="card !p-0 bg-white shadow-lg overflow-visible">
	<BuilderMinimap frameworkId={framework.id} />

	<div class="max-w-3xl mx-auto px-6 py-8 space-y-8">
		<!-- Framework metadata -->
		<div class="space-y-2">
			<input
				type="text"
				value={$frameworkStore.name}
				placeholder="Framework name"
				class="w-full text-2xl font-bold bg-transparent border-0 border-b-2 border-transparent hover:border-gray-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors py-1"
				onblur={(e) => {
					builder.updateFramework({ name: e.currentTarget.value });
				}}
			/>
			<textarea
				value={$frameworkStore.description ?? ''}
				placeholder="Framework description (optional)"
				rows="2"
				class="w-full text-sm text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none py-1"
				onblur={(e) => {
					builder.updateFramework({ description: e.currentTarget.value || null });
				}}
			></textarea>
			{#if $frameworkStore.urn}
				<button
					type="button"
					class="inline-flex items-center gap-1 text-xs font-mono text-gray-300 hover:text-gray-500 transition-colors truncate max-w-full text-left group/urn"
					onclick={() => {
						navigator.clipboard.writeText($frameworkStore.urn ?? '');
						urnCopied = true;
						setTimeout(() => (urnCopied = false), 1500);
					}}
				>
					<i class="fa-solid {urnCopied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"></i>
					{#if urnCopied}
						<span class="text-green-500">Copied!</span>
					{:else}
						{$frameworkStore.urn}
					{/if}
				</button>
			{/if}
			{#if $errorsStore.has('framework')}
				<p class="text-xs text-red-600">{$errorsStore.get('framework')}</p>
			{/if}
		</div>

		<!-- Outcome rules -->
		<OutcomesEditor
			outcomes={$frameworkStore.outcomes_definition ?? []}
			onupdate={(rules) => builder.updateFramework({ outcomes_definition: rules })}
		/>

		<!-- Sections -->
		{#each $sectionsStore as section, sectionIndex (section.node.id)}
			<!-- Add section button between sections -->
			{#if sectionIndex > 0}
				<button
					type="button"
					class="w-full py-2 border-2 border-dashed border-gray-200 rounded-lg text-xs text-gray-300 hover:text-gray-500 hover:border-gray-300 transition-colors opacity-0 hover:opacity-100"
					onclick={() => builder.addSection(sectionIndex - 1)}
				>
					<i class="fa-solid fa-plus mr-1"></i>Insert section
				</button>
			{/if}

			<div
				class:opacity-50={draggedSectionIndex === sectionIndex}
				draggable="true"
				ondragstart={() => handleSectionDragStart(sectionIndex)}
				ondragover={handleSectionDragOver}
				ondrop={(e) => handleSectionDrop(e, sectionIndex)}
				ondragend={handleSectionDragEnd}
				role="listitem"
			>
				<SectionBlock {section} {sectionIndex} />
			</div>
		{/each}

		<!-- Add section at bottom -->
		<button
			type="button"
			class="w-full py-4 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-400 hover:text-gray-600 hover:border-gray-400 transition-colors"
			onclick={() => builder.addSection()}
		>
			<i class="fa-solid fa-plus mr-1"></i>Add section
		</button>

		<!-- Empty state -->
		{#if $sectionsStore.length === 0}
			<div class="text-center py-16">
				<div
					class="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center"
				>
					<i class="fa-solid fa-layer-group text-2xl text-gray-400"></i>
				</div>
				<h3 class="text-lg font-medium text-gray-600 mb-1">No sections yet</h3>
				<p class="text-sm text-gray-400 mb-4">Start building your framework by adding a section.</p>
				<button
					type="button"
					class="btn preset-filled-primary-500 px-6"
					onclick={() => builder.addSection()}
				>
					<i class="fa-solid fa-plus mr-2"></i>Add first section
				</button>
			</div>
		{/if}

		<!-- Global errors -->
		{#each [...$errorsStore.entries()] as [key, message] (key)}
			{#if key.startsWith('add-') || key.startsWith('reorder-')}
				<div class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-600">
					{message}
				</div>
			{/if}
		{/each}
	</div>
</div>
