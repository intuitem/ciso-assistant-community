<script lang="ts">
	import { getBuilderContext } from './builder-state.svelte';

	const state = getBuilderContext();

	function scrollToSection(sectionId: string) {
		const el = document.querySelector(`[data-section-id="${sectionId}"]`);
		if (el) {
			el.scrollIntoView({ behavior: 'smooth', block: 'start' });
			state.activeSection = sectionId;
		}
	}
</script>

<div class="sticky top-0 z-10 bg-white/95 backdrop-blur-sm border-b border-gray-200 shadow-sm">
	<div class="max-w-3xl mx-auto flex items-center gap-2 py-3 px-4 overflow-x-auto">
		<span class="text-xs font-medium text-gray-500 uppercase tracking-wider shrink-0">Sections</span
		>
		{#each state.sections as section (section.node.id)}
			<button
				type="button"
				class="shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-colors {state.activeSection ===
				section.node.id
					? 'bg-blue-600 text-white'
					: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
				onclick={() => scrollToSection(section.node.id)}
			>
				{section.node.ref_id || section.node.name || 'Untitled'}
			</button>
		{/each}
		{#if state.sections.length === 0}
			<span class="text-xs text-gray-400">No sections yet</span>
		{/if}

		{#if state.saving}
			<span class="ml-auto shrink-0 text-xs text-gray-400 flex items-center gap-1">
				<i class="fa-solid fa-circle-notch fa-spin text-xs"></i> Saving...
			</span>
		{/if}
	</div>
</div>
