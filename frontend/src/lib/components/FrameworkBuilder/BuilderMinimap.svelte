<script lang="ts">
	import { onMount } from 'svelte';
	import { getBuilderContext } from './builder-state';
	import { localeLabel } from './builder-utils.svelte';

	interface Props {
		frameworkId: string;
	}

	let { frameworkId }: Props = $props();

	const builder = getBuilderContext();
	const {
		saving: savingStore,
		errors: errorsStore,
		unsaved: unsavedStore,
		unpublished: unpublishedStore,
		framework: frameworkStore,
		activeLanguage: activeLanguageStore
	} = builder;

	let topOffset = $state(0);
	let confirmPublish = $state(false);
	let confirmDiscard = $state(false);
	let publishing = $state(false);
	let discarding = $state(false);
	let publishSuccess = $state(false);
	let confirmCopyBase = $state(false);

	let translationProgress = $derived.by(() => {
		if (!$activeLanguageStore) return null;
		return builder.getTranslationProgress($activeLanguageStore);
	});

	onMount(() => {
		const appBar = document.querySelector('[data-scope="app-bar"]');
		if (appBar) {
			topOffset = appBar.getBoundingClientRect().height;
		}
	});

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
	<div class="flex items-center gap-3 py-2 px-4">
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

		<!-- Export YAML button -->
		<a
			href="/frameworks/{frameworkId}/builder?_action=export-yaml"
			class="shrink-0 text-xs text-gray-500 hover:text-gray-700 transition-colors px-2 py-1 flex items-center gap-1"
			download
			title={$unpublishedStore
				? "Unpublished changes won't be included. Publish first to export latest edits."
				: 'Export framework as YAML library file'}
		>
			<i class="fa-solid fa-file-export text-[10px]"></i>
			Export YAML
			{#if $unpublishedStore}
				<i class="fa-solid fa-triangle-exclamation text-amber-500 text-[10px]"></i>
			{/if}
		</a>

		<!-- Language selector -->
		{#if ($frameworkStore.available_languages ?? []).length > 0}
			<div class="h-4 w-px bg-gray-200 shrink-0"></div>
			<div class="flex items-center gap-1.5 shrink-0">
				<i class="fa-solid fa-language text-gray-400 text-xs"></i>
				<select
					value={$activeLanguageStore ?? ''}
					class="text-xs border border-gray-200 rounded px-1.5 py-1 focus:border-blue-500 outline-none bg-white cursor-pointer"
					onchange={(e) => builder.setActiveLanguage(e.currentTarget.value || null)}
				>
					<option value="">No translation</option>
					{#each $frameworkStore.available_languages ?? [] as lang}
						<option value={lang}>{localeLabel(lang)}</option>
					{/each}
				</select>
				{#if translationProgress}
					<span
						class="text-xs tabular-nums {translationProgress.translated ===
						translationProgress.total
							? 'text-green-600'
							: 'text-amber-600'}"
					>
						{translationProgress.translated}/{translationProgress.total}
					</span>
				{/if}
				{#if $activeLanguageStore}
					{#if confirmCopyBase}
						<span class="text-xs text-amber-600">Copy base text?</span>
						<button
							type="button"
							class="text-xs text-amber-700 font-medium px-1.5 py-0.5 rounded bg-amber-50 hover:bg-amber-100"
							onclick={() => {
								builder.copyFromBase($activeLanguageStore!);
								confirmCopyBase = false;
							}}
						>
							Yes
						</button>
						<button
							type="button"
							class="text-xs text-gray-500 px-1"
							onclick={() => (confirmCopyBase = false)}
						>
							No
						</button>
					{:else}
						<button
							type="button"
							class="text-xs text-gray-400 hover:text-amber-600 transition-colors px-1.5 py-0.5"
							title="Copy base language text to {$activeLanguageStore?.toUpperCase()} (won't overwrite existing translations)"
							onclick={() => (confirmCopyBase = true)}
						>
							<i class="fa-solid fa-copy mr-0.5"></i>Copy base
						</button>
					{/if}
				{/if}
			</div>
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
