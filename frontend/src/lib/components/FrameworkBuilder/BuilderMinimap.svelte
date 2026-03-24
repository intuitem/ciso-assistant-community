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
		saving: savingStore,
		errors: errorsStore
	} = builder;

	let topOffset = $state(0);
	let confirmPublish = $state(false);
	let confirmDiscard = $state(false);
	let publishing = $state(false);
	let discarding = $state(false);
	let publishSuccess = $state(false);

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

	async function handlePublish() {
		publishing = true;
		try {
			await builder.publish();
			publishSuccess = true;
			confirmPublish = false;
			setTimeout(() => {
				window.location.href = `/frameworks/${frameworkId}`;
			}, 1000);
		} catch {
			// Error is already in the errors store
		} finally {
			publishing = false;
		}
	}

	async function handleDiscard() {
		discarding = true;
		try {
			await builder.discard();
			confirmDiscard = false;
			window.location.href = `/frameworks/${frameworkId}`;
		} catch {
			// Error is already in the errors store
		} finally {
			discarding = false;
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

		<!-- Draft badge -->
		<span class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
			Draft
		</span>

		{#each $sectionsStore as section (section.node.id)}
			<button
				type="button"
				class="shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors {$activeSectionStore ===
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

		<!-- Spacer -->
		<div class="ml-auto"></div>

		<!-- Saving indicator -->
		{#if $savingStore}
			<span class="shrink-0 text-xs text-gray-400 flex items-center gap-1">
				<i class="fa-solid fa-circle-notch fa-spin text-xs"></i> Saving draft...
			</span>
		{/if}

		<!-- Save error -->
		{#if $errorsStore.has('save-draft')}
			<span class="shrink-0 text-xs text-red-600 flex items-center gap-1" title={$errorsStore.get('save-draft')}>
				<i class="fa-solid fa-triangle-exclamation text-xs"></i> Save failed
			</span>
		{/if}

		<!-- Publish success -->
		{#if publishSuccess}
			<span class="shrink-0 text-xs text-green-600 flex items-center gap-1">
				<i class="fa-solid fa-check text-xs"></i> Published! Redirecting...
			</span>
		{/if}

		<!-- Discard button -->
		{#if confirmDiscard}
			<span class="shrink-0 text-xs text-red-600 font-medium">Discard all changes?</span>
			<button
				type="button"
				class="shrink-0 text-xs text-red-600 font-medium px-2 py-1 rounded bg-red-50 hover:bg-red-100 transition-colors"
				disabled={discarding}
				onclick={handleDiscard}
			>
				{#if discarding}
					<i class="fa-solid fa-circle-notch fa-spin mr-1"></i>
				{/if}
				Yes, discard
			</button>
			<button
				type="button"
				class="shrink-0 text-xs text-gray-500 px-2 py-1"
				onclick={() => (confirmDiscard = false)}
			>
				Cancel
			</button>
		{:else}
			<button
				type="button"
				class="shrink-0 text-xs text-gray-400 hover:text-red-500 transition-colors px-2 py-1"
				title="Discard draft"
				onclick={() => (confirmDiscard = true)}
			>
				<i class="fa-solid fa-trash-can mr-1"></i>Discard
			</button>
		{/if}

		<div class="h-4 w-px bg-gray-200 shrink-0"></div>

		<!-- Publish button -->
		{#if confirmPublish}
			<span class="shrink-0 text-xs text-blue-600 font-medium">Publish to live?</span>
			<button
				type="button"
				class="shrink-0 text-xs text-white font-medium px-3 py-1 rounded bg-blue-600 hover:bg-blue-700 transition-colors"
				disabled={publishing}
				onclick={handlePublish}
			>
				{#if publishing}
					<i class="fa-solid fa-circle-notch fa-spin mr-1"></i>Publishing...
				{:else}
					Confirm
				{/if}
			</button>
			<button
				type="button"
				class="shrink-0 text-xs text-gray-500 px-2 py-1"
				onclick={() => (confirmPublish = false)}
			>
				Cancel
			</button>
		{:else}
			<button
				type="button"
				class="shrink-0 text-xs text-white font-medium px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors flex items-center gap-1.5"
				title="Publish draft to live framework"
				onclick={() => (confirmPublish = true)}
			>
				<i class="fa-solid fa-rocket text-[10px]"></i>
				Publish
			</button>
		{/if}
	</div>
</div>
