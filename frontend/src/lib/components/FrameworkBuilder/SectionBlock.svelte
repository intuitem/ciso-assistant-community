<script lang="ts">
	import { slide } from 'svelte/transition';
	import {
		getBuilderContext,
		getTranslation,
		withTranslation,
		type BuilderSection
	} from './builder-state';
	import { createHandleGatedDragHandlers } from './builder-utils.svelte';
	import ConfirmAction from './ConfirmAction.svelte';
	import RequirementBlock from './RequirementBlock.svelte';
	import SplashScreenBlock from './SplashScreenBlock.svelte';

	interface Props {
		section: BuilderSection;
		sectionIndex: number;
	}

	let { section, sectionIndex }: Props = $props();

	const builder = getBuilderContext();
	const { errors: errorsStore, activeLanguage: activeLanguageStore } = builder;
	let collapsed = $state(section.collapsed);

	// Drag state for requirements within this section
	const reqDrag = createHandleGatedDragHandlers((from, to) =>
		builder.reorderRequirements(section.node.id, from, to)
	);

	async function saveField(field: string, value: unknown) {
		await builder.updateNode(section.node.id, { [field]: value });
	}
</script>

<div data-section-id={section.node.id} class="scroll-mt-32">
	<!-- Section header -->
	<div class="flex items-center gap-3 group mb-3">
		<span class="cursor-grab text-gray-300 group-hover:text-gray-400" data-drag-handle>
			<i class="fa-solid fa-grip-vertical text-sm"></i>
		</span>

		<input
			type="text"
			value={section.node.ref_id ?? ''}
			placeholder="ID"
			class="w-20 text-xs font-mono bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors text-gray-500"
			onblur={(e) => saveField('ref_id', e.currentTarget.value || null)}
		/>

		{#if $activeLanguageStore}
			<div class="flex-1 grid grid-cols-2 gap-3">
				<input
					type="text"
					value={section.node.name ?? ''}
					readonly
					class="text-xl font-semibold bg-transparent border-0 border-b border-transparent py-0.5 text-gray-400 cursor-default"
				/>
				<input
					type="text"
					value={getTranslation(section.node.translations, $activeLanguageStore, 'name')}
					placeholder="Translate section name..."
					class="text-xl font-semibold bg-transparent border-0 border-b border-transparent hover:border-blue-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors"
					onblur={(e) =>
						saveField(
							'translations',
							withTranslation(
								section.node.translations,
								$activeLanguageStore!,
								'name',
								e.currentTarget.value
							)
						)}
				/>
			</div>
		{:else}
			<input
				type="text"
				value={section.node.name ?? ''}
				placeholder="Section name"
				class="flex-1 text-xl font-semibold bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors"
				onblur={(e) => saveField('name', e.currentTarget.value || null)}
			/>
		{/if}

		<button
			type="button"
			class="text-gray-400 hover:text-gray-600 transition-colors"
			onclick={() => (collapsed = !collapsed)}
		>
			<i class="fa-solid {collapsed ? 'fa-chevron-right' : 'fa-chevron-down'} text-sm"></i>
		</button>

		<ConfirmAction
			message="Delete section and all contents?"
			onconfirm={() => builder.deleteSection(sectionIndex)}
			confirmLabel="Delete"
			triggerClass="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 transition-all"
			confirmClass="text-xs text-red-600 font-medium px-2 py-1 rounded bg-red-50 hover:bg-red-100"
		/>
	</div>

	{#if $errorsStore.has(`node-${section.node.id}`)}
		<p class="text-xs text-red-600 ml-8 mb-2">
			{$errorsStore.get(`node-${section.node.id}`)}
		</p>
	{/if}

	<!-- Section children -->
	{#if !collapsed}
		<div transition:slide={{ duration: 200 }} class="space-y-4 ml-4">
			{#each section.children as req, reqIndex (req.node.id)}
				<div
					class:opacity-50={reqDrag.draggedIndex === reqIndex}
					draggable="true"
					onmousedown={reqDrag.recordMousedown}
					ondragstart={(e) => reqDrag.handleDragStart(e, reqIndex)}
					ondragover={reqDrag.handleDragOver}
					ondrop={(e) => reqDrag.handleDrop(e, reqIndex)}
					ondragend={reqDrag.handleDragEnd}
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
