<script lang="ts">
	import { onMount } from 'svelte';
	import { getBuilderContext } from './builder-state';
	import { localeLabel } from './builder-utils.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		frameworkId: string;
		/** Toolbar link overrides for non-live hosts (null preview hides the link) */
		links?: { back?: string; preview?: string | null; exportYaml?: string } | null;
		onOpenHelp?: () => void;
		onExpandAllCards?: () => void;
		onCollapseAllCards?: () => void;
	}

	let {
		frameworkId,
		links = null,
		onOpenHelp,
		onExpandAllCards,
		onCollapseAllCards
	}: Props = $props();

	const builder = getBuilderContext();

	let backHref = $derived(links?.back ?? `/frameworks/${frameworkId}`);
	// Tri-state: undefined → default live-framework preview, null → hidden.
	// The standalone /frameworks/{id}/builder routes are retired: hosts must
	// provide these links explicitly (the library builder does).
	let previewHref = $derived(links?.preview ?? null);
	let exportHref = $derived(links?.exportYaml ?? null);
	const {
		saving: savingStore,
		errors: errorsStore,
		unsaved: unsavedStore,
		rootNodes: rootNodesStore,
		framework: frameworkStore,
		activeLanguage: activeLanguageStore
	} = builder;

	let topOffset = $state(0);
	let confirmCopyBase = $state(false);

	let translationProgress = $derived.by(() => {
		if (!$activeLanguageStore) return null;
		return builder.getTranslationProgress($activeLanguageStore);
	});

	// The library-draft document is the single draft layer: the only lifecycle
	// state the editor owns is saved-vs-unsaved. Publishing (loading the
	// library) happens on the library page.
	let hasDraftContent = $derived($rootNodesStore.length > 0);

	onMount(() => {
		const appBar = document.querySelector('[data-scope="app-bar"]');
		if (appBar) {
			topOffset = appBar.getBoundingClientRect().height;
		}
	});
</script>

<div
	class="sticky z-40 bg-surface-50-950 border-b border-surface-200-800 shadow-sm rounded-t-lg"
	style="top: {topOffset}px"
>
	<div class="flex items-center gap-3 py-2 px-4">
		<a
			href={backHref}
			class="text-sm text-surface-500 hover:text-surface-600-400 transition-colors shrink-0"
		>
			<i class="fa-solid fa-arrow-left"></i>
		</a>

		<div class="h-4 w-px bg-surface-200-800 shrink-0"></div>

		<!-- Saved-vs-unsaved status: the library-draft document is the single
		     draft layer, publishing happens on the library page. -->
		{#if $unsavedStore}
			<span
				class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 inline-flex items-center gap-1"
				title={m.builderStatusUnsavedTitle()}
			>
				<i class="fa-solid fa-pen-nib text-[10px]"></i>
				{m.builderStatusUnsaved()}
			</span>
		{:else if hasDraftContent}
			<span
				class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 inline-flex items-center gap-1"
				title={m.builderStatusSavedTitle()}
			>
				<i class="fa-solid fa-circle-check text-[10px]"></i>
				{m.builderStatusSaved()}
			</span>
		{:else}
			<span
				class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-surface-100-900 text-surface-600-400 inline-flex items-center gap-1"
				title={m.builderStatusEmptyTitle()}
			>
				<i class="fa-solid fa-file-lines text-[10px]"></i>
				{m.builderStatusEmpty()}
			</span>
		{/if}

		<!-- Preview button -->
		{#if previewHref === null}
			<!-- host has no respondent preview route -->
		{:else if $unsavedStore}
			<span
				class="shrink-0 text-xs text-gray-300 px-2 py-1 flex items-center gap-1 cursor-not-allowed"
				title={m.builderPreviewSaveFirst()}
			>
				<i class="fa-solid fa-eye text-[10px]"></i>
				{m.builderPreview()}
			</span>
		{:else}
			<a
				href={previewHref}
				target="_blank"
				rel="noopener noreferrer"
				class="shrink-0 text-xs text-purple-600 hover:text-purple-800 transition-colors px-2 py-1 flex items-center gap-1"
				title={m.builderPreviewAsRespondent()}
			>
				<i class="fa-solid fa-eye text-[10px]"></i>
				{m.builderPreview()}
			</a>
		{/if}

		<!-- Export YAML button (exports the saved document) -->
		{#if exportHref}
			<a
				href={exportHref}
				class="shrink-0 text-xs text-surface-600-400 hover:text-surface-700-300 transition-colors px-2 py-1 flex items-center gap-1"
				download
				title={$unsavedStore ? m.builderExportUnsavedTitle() : m.builderExportYamlTitle()}
			>
				<i class="fa-solid fa-file-export text-[10px]"></i>
				{m.exportYaml()}
				{#if $unsavedStore}
					<i class="fa-solid fa-triangle-exclamation text-amber-500 text-[10px]"></i>
				{/if}
			</a>
		{/if}

		<!-- Language selector -->
		{#if ($frameworkStore.available_languages ?? []).length > 0}
			<div class="h-4 w-px bg-surface-200-800 shrink-0"></div>
			<div class="flex items-center gap-1.5 shrink-0">
				<i class="fa-solid fa-language text-surface-500 text-xs"></i>
				<select
					value={$activeLanguageStore ?? ''}
					class="text-xs border border-surface-200-800 rounded px-1.5 py-1 focus:border-blue-500 outline-none bg-surface-50-950 cursor-pointer"
					onchange={(e) => builder.setActiveLanguage(e.currentTarget.value || null)}
				>
					<option value="">{m.builderNoTranslation()}</option>
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
						<span class="text-xs text-amber-600">{m.builderCopyBaseQuestion()}</span>
						<button
							type="button"
							class="text-xs text-amber-700 font-medium px-1.5 py-0.5 rounded bg-amber-50 hover:bg-amber-100"
							onclick={() => {
								builder.copyFromBase($activeLanguageStore!);
								confirmCopyBase = false;
							}}
						>
							{m.yes()}
						</button>
						<button
							type="button"
							class="text-xs text-surface-600-400 px-1"
							onclick={() => (confirmCopyBase = false)}
						>
							{m.no()}
						</button>
					{:else}
						<button
							type="button"
							class="text-xs text-surface-500 hover:text-amber-600 transition-colors px-1.5 py-0.5"
							title={m.builderCopyBaseTitle({ lang: $activeLanguageStore?.toUpperCase() ?? '' })}
							onclick={() => (confirmCopyBase = true)}
						>
							<i class="fa-solid fa-copy mr-0.5"></i>{m.builderCopyBase()}
						</button>
					{/if}
				{/if}
			</div>
		{/if}

		<!-- Spacer -->
		<div class="ml-auto"></div>

		<!-- Collapse/expand all cards -->
		{#if onCollapseAllCards}
			<button
				type="button"
				class="shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-md text-xs text-surface-500 hover:text-surface-600-400 hover:bg-surface-100-900 transition-colors"
				onclick={onCollapseAllCards}
				title={m.builderCollapseAllCards()}
				aria-label={m.builderCollapseAllCards()}
			>
				<i class="fa-solid fa-angles-up text-[10px]"></i>
			</button>
		{/if}
		{#if onExpandAllCards}
			<button
				type="button"
				class="shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-md text-xs text-surface-500 hover:text-surface-600-400 hover:bg-surface-100-900 transition-colors"
				onclick={onExpandAllCards}
				title={m.builderExpandAllCards()}
				aria-label={m.builderExpandAllCards()}
			>
				<i class="fa-solid fa-angles-down text-[10px]"></i>
			</button>
		{/if}

		<!-- Keyboard shortcut help -->
		{#if onOpenHelp}
			<button
				type="button"
				class="shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full text-xs text-surface-500 hover:text-surface-600-400 hover:bg-surface-100-900 transition-colors"
				onclick={onOpenHelp}
				title={m.builderKeyboardShortcutsHint()}
				aria-label={m.builderShowKeyboardShortcuts()}
			>
				?
			</button>
		{/if}

		<!-- Save button (visible when local edits not yet saved to draft) -->
		{#if $unsavedStore}
			<button
				type="button"
				class="shrink-0 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5
					{$savingStore ? 'bg-gray-400 text-white cursor-wait' : 'bg-gray-600 text-white hover:bg-gray-700'}"
				disabled={$savingStore}
				onclick={() => builder.flushDraft()}
				title={m.builderSaveDraftTitle()}
			>
				{#if $savingStore}
					<i class="fa-solid fa-circle-notch fa-spin text-[10px]"></i>
					{m.saving()}
				{:else}
					<i class="fa-solid fa-floppy-disk text-[10px]"></i>
					{m.save()}
				{/if}
			</button>
		{/if}

		<!-- Save error -->
		{#if $errorsStore.has('save-draft')}
			<span
				class="shrink-0 text-xs text-red-600 flex items-center gap-1"
				title={$errorsStore.get('save-draft')}
			>
				<i class="fa-solid fa-triangle-exclamation text-xs"></i>
				{m.builderSaveFailed()}
			</span>
		{/if}
	</div>
</div>
