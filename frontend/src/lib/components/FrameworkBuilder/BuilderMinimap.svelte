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
		errors: errorsStore,
		unsaved: unsavedStore,
		unpublished: unpublishedStore
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
			builder.unsaved.set(false);
			builder.unpublished.set(false);
			setTimeout(() => (publishSuccess = false), 3000);
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
	<div class="flex items-center gap-3 py-2 px-4 overflow-x-auto">
		<a
			href="/frameworks/{frameworkId}"
			class="text-sm text-gray-400 hover:text-gray-600 transition-colors shrink-0"
		>
			<i class="fa-solid fa-arrow-left"></i>
		</a>

		<div class="h-4 w-px bg-gray-200 shrink-0"></div>

		<!-- Draft badge (visible when draft differs from published state) -->
		{#if $unpublishedStore}
			<span
				class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700"
			>
				Draft
			</span>
		{/if}

		<!-- Preview button -->
		{#if $unsavedStore}
			<span
				class="shrink-0 text-xs text-gray-300 px-2 py-1 flex items-center gap-1 cursor-not-allowed"
				title="Save your draft first to preview"
			>
				<i class="fa-solid fa-eye text-[10px]"></i>
				Preview
			</span>
		{:else}
			<a
				href="/frameworks/{frameworkId}/builder/preview"
				target="_blank"
				rel="noopener noreferrer"
				class="shrink-0 text-xs text-purple-600 hover:text-purple-800 transition-colors px-2 py-1 flex items-center gap-1"
				title="Preview as respondent (opens in new tab)"
			>
				<i class="fa-solid fa-eye text-[10px]"></i>
				Preview
			</a>
		{/if}

		<div class="h-4 w-px bg-gray-200 shrink-0"></div>

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

		<!-- Save button (visible when local edits not yet saved to draft) -->
		{#if $unsavedStore}
			<button
				type="button"
				class="shrink-0 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5
					{$savingStore ? 'bg-gray-400 text-white cursor-wait' : 'bg-gray-600 text-white hover:bg-gray-700'}"
				disabled={$savingStore}
				onclick={() => builder.flushDraft()}
				title="Save draft (Ctrl+S)"
			>
				{#if $savingStore}
					<i class="fa-solid fa-circle-notch fa-spin text-[10px]"></i>
					Saving...
				{:else}
					<i class="fa-solid fa-floppy-disk text-[10px]"></i>
					Save
				{/if}
			</button>
		{/if}

		<!-- Save error -->
		{#if $errorsStore.has('save-draft')}
			<span
				class="shrink-0 text-xs text-red-600 flex items-center gap-1"
				title={$errorsStore.get('save-draft')}
			>
				<i class="fa-solid fa-triangle-exclamation text-xs"></i> Save failed
			</span>
		{/if}

		<!-- Publish success -->
		{#if publishSuccess}
			<span class="shrink-0 text-xs text-green-600 flex items-center gap-1">
				<i class="fa-solid fa-check text-xs"></i> Published!
			</span>
		{/if}

		<!-- Discard/Publish buttons (visible when draft differs from published state) -->
		{#if !$unpublishedStore}
			<!-- No changes — nothing to discard or publish -->
		{:else if confirmDiscard}
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

		{#if $unpublishedStore}
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
		{/if}
	</div>
</div>
