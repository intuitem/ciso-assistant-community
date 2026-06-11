<script lang="ts">
	import { onMount } from 'svelte';
	import { getBuilderContext } from './builder-state';
	import { localeLabel } from './builder-utils.svelte';
	import { apiPublishDraftPreview, type PublishPreview } from './builder-api';
	import { m } from '$paraglide/messages';

	interface Props {
		frameworkId: string;
		onOpenHelp?: () => void;
		onExpandAllCards?: () => void;
		onCollapseAllCards?: () => void;
	}

	let { frameworkId, onOpenHelp, onExpandAllCards, onCollapseAllCards }: Props = $props();

	const builder = getBuilderContext();
	const {
		saving: savingStore,
		errors: errorsStore,
		unsaved: unsavedStore,
		unpublished: unpublishedStore,
		rootNodes: rootNodesStore,
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
	let publishPreview = $state<PublishPreview | null>(null);
	let loadingPreview = $state(false);

	let translationProgress = $derived.by(() => {
		if (!$activeLanguageStore) return null;
		return builder.getTranslationProgress($activeLanguageStore);
	});

	// Live-vs-draft status. The framework is always pickable by audit authors;
	// what varies is whether any live content exists and whether the draft
	// differs from live.
	// - hasLiveContent: true iff the framework has ever been published (editing_version > 1).
	// - hasDraftContent: the in-editor tree has at least one node.
	let hasLiveContent = $derived(($frameworkStore.editing_version ?? 1) > 1);
	let hasDraftContent = $derived($rootNodesStore.length > 0);

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
			publishPreview = null;
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

		<!--
			Live-vs-draft status badge. The framework is always pickable by audit
			authors; what varies is whether new audits will see the editor's work.
		-->
		{#if hasLiveContent && !$unpublishedStore}
			<span
				class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 inline-flex items-center gap-1"
				title={m.builderStatusLiveTitle()}
			>
				<i class="fa-solid fa-circle-check text-[10px]"></i>
				{m.builderStatusLive()}
			</span>
		{:else if hasLiveContent && $unpublishedStore}
			<span
				class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 inline-flex items-center gap-1"
				title={m.builderStatusUnpublishedChangesTitle()}
			>
				<i class="fa-solid fa-pen-nib text-[10px]"></i>
				{m.builderStatusUnpublishedChanges()}
			</span>
		{:else if hasDraftContent}
			<span
				class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 inline-flex items-center gap-1"
				title={m.builderStatusDraftNothingLiveTitle()}
			>
				<i class="fa-solid fa-triangle-exclamation text-[10px]"></i>
				{m.builderStatusDraftNothingLive()}
			</span>
		{:else}
			<span
				class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 inline-flex items-center gap-1"
				title={m.builderStatusEmptyTitle()}
			>
				<i class="fa-solid fa-file-lines text-[10px]"></i>
				{m.builderStatusEmpty()}
			</span>
		{/if}

		<!-- Preview button -->
		{#if $unsavedStore}
			<span
				class="shrink-0 text-xs text-gray-300 px-2 py-1 flex items-center gap-1 cursor-not-allowed"
				title={m.builderPreviewSaveFirst()}
			>
				<i class="fa-solid fa-eye text-[10px]"></i>
				{m.builderPreview()}
			</span>
		{:else}
			<a
				href="/frameworks/{frameworkId}/builder/preview"
				target="_blank"
				rel="noopener noreferrer"
				class="shrink-0 text-xs text-purple-600 hover:text-purple-800 transition-colors px-2 py-1 flex items-center gap-1"
				title={m.builderPreviewAsRespondent()}
			>
				<i class="fa-solid fa-eye text-[10px]"></i>
				{m.builderPreview()}
			</a>
		{/if}

		<!-- Export YAML button -->
		<a
			href="/frameworks/{frameworkId}/builder?_action=export-yaml"
			class="shrink-0 text-xs text-gray-500 hover:text-gray-700 transition-colors px-2 py-1 flex items-center gap-1"
			download
			title={$unpublishedStore
				? m.builderExportYamlUnpublishedWarning()
				: m.builderExportYamlTitle()}
		>
			<i class="fa-solid fa-file-export text-[10px]"></i>
			{m.exportYaml()}
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
							class="text-xs text-gray-500 px-1"
							onclick={() => (confirmCopyBase = false)}
						>
							{m.no()}
						</button>
					{:else}
						<button
							type="button"
							class="text-xs text-gray-400 hover:text-amber-600 transition-colors px-1.5 py-0.5"
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
				class="shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-md text-xs text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
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
				class="shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-md text-xs text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
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
				class="shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full text-xs text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
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

		<!-- Publish success -->
		{#if publishSuccess}
			<span class="shrink-0 text-xs text-green-600 flex items-center gap-1">
				<i class="fa-solid fa-check text-xs"></i>
				{m.builderPublishedFlash()}
			</span>
		{/if}

		<!-- Discard/Publish buttons (visible when draft differs from published state) -->
		{#if !$unpublishedStore}
			<!-- No changes — nothing to discard or publish -->
		{:else if confirmDiscard}
			<span class="shrink-0 text-xs text-red-600 font-medium"
				>{m.builderDiscardAllChangesQuestion()}</span
			>
			<button
				type="button"
				class="shrink-0 text-xs text-red-600 font-medium px-2 py-1 rounded bg-red-50 hover:bg-red-100 transition-colors"
				disabled={discarding}
				onclick={handleDiscard}
			>
				{#if discarding}
					<i class="fa-solid fa-circle-notch fa-spin mr-1"></i>
				{/if}
				{m.builderYesDiscard()}
			</button>
			<button
				type="button"
				class="shrink-0 text-xs text-gray-500 px-2 py-1"
				onclick={() => (confirmDiscard = false)}
			>
				{m.cancel()}
			</button>
		{:else}
			<button
				type="button"
				class="shrink-0 text-xs text-gray-400 hover:text-red-500 transition-colors px-2 py-1"
				title={m.builderDiscardDraftTitle()}
				onclick={() => (confirmDiscard = true)}
			>
				<i class="fa-solid fa-trash-can mr-1"></i>{m.builderDiscard()}
			</button>
		{/if}

		{#if $unpublishedStore && !$unsavedStore}
			<div class="h-4 w-px bg-gray-200 shrink-0"></div>

			<!-- Publish button (hidden until draft is saved) -->
			<button
				type="button"
				class="shrink-0 text-xs text-white font-medium px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors flex items-center gap-1.5"
				title={m.builderPublishDraftToLiveTitle()}
				disabled={loadingPreview}
				onclick={async () => {
					loadingPreview = true;
					try {
						publishPreview = await apiPublishDraftPreview(frameworkId);
						confirmPublish = true;
					} catch {
						// Fall back to confirmation without preview
						publishPreview = null;
						confirmPublish = true;
					} finally {
						loadingPreview = false;
					}
				}}
			>
				{#if loadingPreview}
					<i class="fa-solid fa-circle-notch fa-spin text-[10px]"></i>
				{:else}
					<i class="fa-solid fa-rocket text-[10px]"></i>
				{/if}
				{m.publish()}
			</button>
		{/if}
	</div>
</div>

{#if confirmPublish}
	<!-- Publish impact preview modal -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
		onkeydown={(e) => e.key === 'Escape' && (confirmPublish = false)}
	>
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
			onclick={(e) => e.stopPropagation()}
		>
			<div class="px-5 py-4 border-b border-gray-200">
				<h3 class="text-lg font-semibold text-gray-900">{m.builderPublishModalTitle()}</h3>
				<p class="text-sm text-gray-500 mt-1">
					{m.builderPublishModalDescription()}
				</p>
			</div>

			<div class="px-5 py-4 space-y-3 max-h-[60vh] overflow-y-auto">
				{#if publishPreview}
					{#if publishPreview.added.requirements > 0}
						<div class="p-3 bg-green-50 border-l-2 border-green-400 rounded-r">
							<div class="text-sm font-medium text-green-800">
								<i class="fa-solid fa-plus mr-1"></i>
								{m.builderRequirementAdded({
									count: publishPreview.added.requirements
								})}
								{#if publishPreview.added.questions > 0}
									, {m.builderQuestionsAddedSuffix({
										count: publishPreview.added.questions
									})}
								{/if}
							</div>
							{#if publishPreview.added.details.length > 0}
								<ul class="mt-1.5 text-xs text-green-700 space-y-0.5">
									{#each publishPreview.added.details as node}
										<li class="truncate" title={node.name}>{node.name}</li>
									{/each}
								</ul>
							{/if}
						</div>
					{/if}

					{#if publishPreview.removed.requirements > 0}
						<div class="p-3 bg-red-50 border-l-2 border-red-400 rounded-r">
							<div class="text-sm font-medium text-red-800">
								<i class="fa-solid fa-trash mr-1"></i>
								{m.builderRequirementRemoved({
									count: publishPreview.removed.requirements
								})}
								{#if publishPreview.removed.questions > 0}
									, {m.builderQuestionsRemovedSuffix({
										count: publishPreview.removed.questions
									})}
								{/if}
							</div>
							{#if publishPreview.removed.details.length > 0}
								<ul class="mt-1.5 text-xs text-red-700 space-y-0.5">
									{#each publishPreview.removed.details as node}
										<li class="truncate" title={node.name}>{node.name}</li>
									{/each}
								</ul>
							{/if}
						</div>
					{/if}

					{#if publishPreview.added.requirements === 0 && publishPreview.removed.requirements === 0}
						<div class="p-3 bg-gray-50 border-l-2 border-gray-300 rounded-r">
							<div class="text-sm text-gray-600">
								<i class="fa-solid fa-equals mr-1"></i>
								{m.builderNoStructuralChanges()}
							</div>
						</div>
					{/if}

					{#if publishPreview.breaking_changes?.length > 0}
						<div class="p-3 bg-orange-50 border-l-2 border-orange-500 rounded-r">
							<div class="text-sm font-medium text-orange-800">
								<i class="fa-solid fa-bolt mr-1"></i>
								{m.builderBreakingChangesDetected({
									count: publishPreview.breaking_changes.length
								})}
							</div>
							<ul class="mt-1.5 text-xs text-orange-700 space-y-0.5">
								{#each publishPreview.breaking_changes as change}
									<li class="truncate" title="{change.type}: {change.name} ({change.field})">
										<span class="font-mono">{change.field}</span>
										{m.builderChangedOn()}
										{change.type}
										<span class="font-medium">{change.name}</span>
									</li>
								{/each}
							</ul>
							<p class="mt-1.5 text-xs text-orange-600">
								{m.builderBreakingChangesHint()}
							</p>
						</div>
					{/if}

					{#if publishPreview.affected_audits.length > 0}
						<div class="p-3 bg-amber-50 border-l-2 border-amber-400 rounded-r">
							<div class="text-sm font-medium text-amber-800">
								<i class="fa-solid fa-triangle-exclamation mr-1"></i>
								{m.builderAffectedAudits({
									count: publishPreview.affected_audits.length
								})}
							</div>
							<ul class="mt-1.5 text-xs text-amber-700 space-y-0.5">
								{#each publishPreview.affected_audits as audit}
									<li class="truncate" title={audit.name}>{audit.name}</li>
								{/each}
							</ul>
							{#if publishPreview.added.requirements > 0}
								<p class="mt-1.5 text-xs text-amber-600">
									{m.builderAffectedAuditsAddedHint()}
								</p>
							{/if}
							{#if publishPreview.removed.requirements > 0}
								<p class="mt-1.5 text-xs text-amber-600">
									{m.builderAffectedAuditsRemovedHint()}
								</p>
							{/if}
						</div>
					{/if}
				{:else}
					<div class="p-3 bg-gray-50 rounded text-sm text-gray-600">
						{m.builderCouldNotLoadPreview()}
					</div>
				{/if}
			</div>

			<div class="px-5 py-3 border-t border-gray-200 flex justify-end gap-2">
				<button
					type="button"
					class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
					onclick={() => {
						confirmPublish = false;
						publishPreview = null;
					}}
				>
					{m.cancel()}
				</button>
				<button
					type="button"
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
					disabled={publishing}
					onclick={handlePublish}
				>
					{#if publishing}
						<i class="fa-solid fa-circle-notch fa-spin mr-1"></i>{m.builderPublishing()}
					{:else}
						{m.builderConfirmPublish()}
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
