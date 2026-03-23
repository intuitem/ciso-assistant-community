<script lang="ts">
	import { slide } from 'svelte/transition';
	import { getBuilderContext, type BuilderSection } from './builder-state';
	import RequirementBlock from './RequirementBlock.svelte';
	import SplashScreenBlock from './SplashScreenBlock.svelte';

	interface Props {
		section: BuilderSection;
		sectionIndex: number;
	}

	let { section, sectionIndex }: Props = $props();

	const builder = getBuilderContext();
	const { errors: errorsStore } = builder;
	let confirmDelete = $state(false);
	let collapsed = $state(section.collapsed);

	// Drag state for requirements within this section
	let draggedReqIndex: number | null = $state(null);

	async function saveField(field: string, value: unknown) {
		await builder.updateNode(section.node.id, { [field]: value });
	}

	function handleReqDragStart(index: number) {
		draggedReqIndex = index;
	}

	function handleReqDragOver(e: DragEvent) {
		e.preventDefault();
	}

	function handleReqDrop(e: DragEvent, dropIndex: number) {
		e.preventDefault();
		if (draggedReqIndex === null || draggedReqIndex === dropIndex) return;
		builder.reorderRequirements(section.node.id, draggedReqIndex, dropIndex);
		draggedReqIndex = null;
	}

	function handleReqDragEnd() {
		draggedReqIndex = null;
	}
</script>

<div data-section-id={section.node.id} class="scroll-mt-32">
	<!-- Section header -->
	<div class="flex items-center gap-3 group mb-3">
		<span class="cursor-grab text-gray-300 group-hover:text-gray-400">
			<i class="fa-solid fa-grip-vertical text-sm"></i>
		</span>

		<input
			type="text"
			value={section.node.ref_id ?? ''}
			placeholder="ID"
			class="w-20 text-xs font-mono bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors text-gray-500"
			onblur={(e) => saveField('ref_id', e.currentTarget.value || null)}
		/>

		<input
			type="text"
			value={section.node.name ?? ''}
			placeholder="Section name"
			class="flex-1 text-xl font-semibold bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors"
			onblur={(e) => saveField('name', e.currentTarget.value || null)}
		/>

		<button
			type="button"
			class="text-gray-400 hover:text-gray-600 transition-colors"
			onclick={() => (collapsed = !collapsed)}
		>
			<i class="fa-solid {collapsed ? 'fa-chevron-right' : 'fa-chevron-down'} text-sm"></i>
		</button>

		{#if confirmDelete}
			<span class="text-xs text-red-600 font-medium">Delete section and all contents?</span>
			<button
				type="button"
				class="text-xs text-red-600 font-medium px-2 py-1 rounded bg-red-50 hover:bg-red-100"
				onclick={() => {
					builder.deleteSection(sectionIndex);
					confirmDelete = false;
				}}
			>
				Delete
			</button>
			<button
				type="button"
				class="text-xs text-gray-500 px-2 py-1"
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
				<i class="fa-solid fa-trash text-sm"></i>
			</button>
		{/if}
	</div>

	{#if $errorsStore.has(`node-${section.node.id}`)}
		<p class="text-xs text-red-600 ml-8 mb-2">
			{$errorsStore.get(`node-${section.node.id}`)}
		</p>
	{/if}

	<!-- Section children -->
	{#if !collapsed}
		<div transition:slide={{ duration: 200 }} class="space-y-4 ml-4">
			{#each section.requirements as req, reqIndex (req.node.id)}
				<div
					class:opacity-50={draggedReqIndex === reqIndex}
					draggable="true"
					ondragstart={() => handleReqDragStart(reqIndex)}
					ondragover={handleReqDragOver}
					ondrop={(e) => handleReqDrop(e, reqIndex)}
					ondragend={handleReqDragEnd}
					role="listitem"
				>
					{#if req.node.display_mode === 'splash'}
					<SplashScreenBlock requirement={req} />
				{:else}
					<RequirementBlock requirement={req} />
				{/if}
				</div>
			{/each}

			<div class="flex gap-2">
				<button
					type="button"
					class="flex-1 py-3 border-2 border-dashed border-gray-200 rounded-lg text-sm text-gray-400 hover:text-gray-600 hover:border-gray-300 transition-colors"
					onclick={() => builder.addRequirement(section.node.id, section.node.urn ?? '')}
				>
					<i class="fa-solid fa-plus mr-1"></i>Add requirement
				</button>
				<button
					type="button"
					class="flex-1 py-3 border-2 border-dashed border-purple-200 rounded-lg text-sm text-purple-300 hover:text-purple-500 hover:border-purple-300 transition-colors"
					onclick={() => builder.addSplashScreen(section.node.id, section.node.urn ?? '')}
				>
					<i class="fa-solid fa-display mr-1"></i>Add splash screen
				</button>
			</div>
		</div>
	{/if}
</div>
