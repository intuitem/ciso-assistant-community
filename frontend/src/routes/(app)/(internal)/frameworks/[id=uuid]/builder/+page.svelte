<script lang="ts">
	import { onMount } from 'svelte';
	import FrameworkBuilder from '$lib/components/FrameworkBuilder/FrameworkBuilder.svelte';
	import { apiStartEditing } from '$lib/components/FrameworkBuilder/builder-api';
	import type { DraftJSON } from '$lib/components/FrameworkBuilder/builder-api';
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let cloning = $state(false);
	let editingDraft = $state<DraftJSON | null>(null);
	let draftLoading = $state(false);
	let draftError = $state<string | null>(null);
	let draftReady = $state(false);

	onMount(async () => {
		if (data.isImported) return;

		// Always call start-editing: it creates the draft if needed,
		// or returns the existing one (idempotent)
		draftLoading = true;
		try {
			const result = await apiStartEditing(data.framework.id);
			editingDraft = result.draft;
			draftReady = true;
		} catch (e) {
			draftError = (e as Error).message;
		} finally {
			draftLoading = false;
		}
	});

	async function cloneFramework() {
		cloning = true;
		try {
			const res = await fetch(`/frameworks/${data.framework.id}/builder`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					endpoint: `frameworks/${data.framework.id}/duplicate`,
					payload: {
						name: `${data.framework.name} (copy)`,
						folder:
							typeof data.framework.folder === 'string'
								? data.framework.folder
								: data.framework.folder.id
					}
				})
			});
			if (res.ok) {
				const newFw = await res.json();
				window.location.href = `/frameworks/${newFw.id}/builder/`;
			}
		} finally {
			cloning = false;
		}
	}
</script>

<div class="min-h-screen">
	{#if data.isImported}
		<!-- Back link for import guard only -->
		<div class="max-w-3xl mx-auto px-4 pt-4">
			<a
				href="/frameworks/{data.framework.id}"
				class="text-sm text-gray-500 hover:text-gray-700 transition-colors"
			>
				<i class="fa-solid fa-arrow-left mr-1"></i>{m.builderBackToFramework()}
			</a>
		</div>
		<!-- Import guard -->
		<div class="max-w-lg mx-auto mt-16 text-center">
			<div
				class="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 flex items-center justify-center"
			>
				<i class="fa-solid fa-lock text-2xl text-amber-600"></i>
			</div>
			<h2 class="text-xl font-semibold text-gray-800 mb-2">{m.builderImportedFramework()}</h2>
			<p class="text-sm text-gray-500 mb-6">
				{m.builderImportedFrameworkDescription()}
			</p>
			<button
				type="button"
				class="btn preset-filled-primary-500 px-6"
				disabled={cloning}
				onclick={cloneFramework}
			>
				{#if cloning}
					<i class="fa-solid fa-circle-notch fa-spin mr-2"></i>{m.builderCreatingCopy()}
				{:else}
					<i class="fa-solid fa-copy mr-2"></i>{m.builderCreateCopyAndEdit()}
				{/if}
			</button>
		</div>
	{:else if draftLoading}
		<div class="flex items-center justify-center py-32">
			<i class="fa-solid fa-circle-notch fa-spin text-2xl text-gray-400 mr-3"></i>
			<span class="text-gray-500">{m.builderLoadingEditor()}</span>
		</div>
	{:else if draftError}
		<div class="max-w-lg mx-auto mt-16 text-center">
			<div class="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
				<i class="fa-solid fa-triangle-exclamation text-2xl text-red-600"></i>
			</div>
			<h2 class="text-xl font-semibold text-gray-800 mb-2">{m.builderFailedToStartEditor()}</h2>
			<p class="text-sm text-red-600 mb-6">{draftError}</p>
			<a href="/frameworks/{data.framework.id}" class="btn preset-filled-primary-500 px-6">
				{m.builderBackToFramework()}
			</a>
		</div>
	{:else if draftReady}
		<FrameworkBuilder
			framework={data.framework}
			requirementNodes={data.requirementNodes}
			questions={data.questions}
			{editingDraft}
		/>
	{/if}
</div>
