<script lang="ts">
	import { onMount } from 'svelte';
	import { getBuilderContext } from './builder-state';

	interface Props {
		frameworkId: string;
	}

	let { frameworkId }: Props = $props();

	const builder = getBuilderContext();
	const {
		sections: sectionsStore,
		activeSection: activeSectionStore,
		saving: savingStore
	} = builder;

	let topOffset = $state(0);

	onMount(() => {
		const appBar = document.querySelector('[data-scope="app-bar"]');
		if (appBar) {
			topOffset = appBar.getBoundingClientRect().height;
		}
	});

	function scrollToSection(sectionId: string) {
		const el = document.querySelector(`[data-section-id="${sectionId}"]`);
		if (el) {
			el.scrollIntoView({ behavior: 'smooth', block: 'start' });
			activeSectionStore.set(sectionId);
		}
	}
</script>

<div
	class="sticky z-40 bg-white border-b border-gray-200 shadow-sm rounded-t-lg"
	style="top: {topOffset}px"
>
	<div class="flex items-center gap-3 py-2 px-4">
		<a
			href="/frameworks/{frameworkId}"
			class="text-sm text-gray-400 hover:text-gray-600 transition-colors shrink-0"
		>
			<i class="fa-solid fa-arrow-left"></i>
		</a>

		<div class="h-4 w-px bg-gray-200 shrink-0"></div>

		{#each $sectionsStore as section (section.node.id)}
			<button
				type="button"
				class="shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-colors {$activeSectionStore ===
				section.node.id
					? 'bg-blue-600 text-white'
					: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
				onclick={() => scrollToSection(section.node.id)}
			>
				{section.node.ref_id || section.node.name || 'Untitled'}
			</button>
		{/each}
		{#if $sectionsStore.length === 0}
			<span class="text-xs text-gray-400">No sections yet</span>
		{/if}

		{#if $savingStore}
			<span class="ml-auto shrink-0 text-xs text-gray-400 flex items-center gap-1">
				<i class="fa-solid fa-circle-notch fa-spin text-xs"></i> Saving...
			</span>
		{/if}
	</div>
</div>
