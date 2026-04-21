<script lang="ts">
	import {
		getBuilderContext,
		getTranslation,
		withTranslation,
		type BuilderNode
	} from './builder-state';
	import { createCopyHandler, createHandleGatedDragHandlers } from './builder-utils.svelte';
	import ConfirmAction from './ConfirmAction.svelte';
	import QuestionEditor from './QuestionEditor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import AddNodeMenu from './AddNodeMenu.svelte';

	interface Props {
		node: BuilderNode;
		parentId?: string | null;
		indexWithinParent?: number;
	}

	let { node, parentId = null, indexWithinParent = 0 }: Props = $props();

	const builder = getBuilderContext();
	const {
		framework: frameworkStore,
		errors: errorsStore,
		activeLanguage: activeLanguageStore
	} = builder;
	const urnCopy = createCopyHandler();

	// --- Splash-specific state (only used when display_mode === 'splash') ---
	let splashMode: 'edit' | 'preview' = $state('edit');
	let uploading = $state(false);
	let textareaEl: HTMLTextAreaElement | undefined = $state();
	let fileInputEl: HTMLInputElement | undefined = $state();
	let splashDescription = $state(node.node.description ?? '');
	let splashTransDescription = $state('');

	$effect(() => {
		splashDescription = node.node.description ?? '';
	});

	$effect(() => {
		const lang = $activeLanguageStore;
		if (lang) {
			splashTransDescription = getTranslation(node.node.translations, lang, 'description');
		}
	});

	// Depth-based color accents for the card's left border
	const depthColors = [
		'border-l-blue-400',
		'border-l-violet-400',
		'border-l-amber-400',
		'border-l-emerald-400'
	];
	const depthColor = $derived(depthColors[node.depth % depthColors.length]);

	// Drag state for direct children
	const childDrag = createHandleGatedDragHandlers((from, to) =>
		builder.reorderNodes(node.node.id, from, to)
	);

	async function saveField(field: string, value: unknown) {
		await builder.updateNode(node.node.id, { [field]: value });
	}

	async function saveDescription() {
		await builder.updateNode(node.node.id, { description: splashDescription || null });
	}

	async function saveTransDescription() {
		const lang = $activeLanguageStore;
		if (!lang) return;
		await builder.updateNode(node.node.id, {
			translations: withTranslation(
				node.node.translations,
				lang,
				'description',
				splashTransDescription
			)
		});
	}

	// Framework ID for splash-screen image upload proxy
	const frameworkId =
		typeof node.node.framework === 'string'
			? node.node.framework
			: (node.node.framework?.id ?? '');
	const proxyUrl = `/frameworks/${frameworkId}/builder`;

	const allQuestions = $derived(node.questions.map((q) => q.question));
	let nameLength = $derived((node.node.name ?? '').length);

	// Status line text
	const statusLine = $derived.by(() => {
		if (node.node.display_mode === 'splash') return 'Splash screen';
		if (node.node.assessable && node.children.length > 0)
			return `Assessable · ${node.children.length} ${node.children.length === 1 ? 'child' : 'children'}`;
		if (node.node.assessable) return 'Assessable leaf';
		if (node.children.length > 0)
			return `Group · ${node.children.length} ${node.children.length === 1 ? 'child' : 'children'}`;
		return 'Empty node';
	});

	// ===== Markdown editor helpers (ported from SplashScreenBlock.svelte) =====

	async function uploadImage(file: File) {
		uploading = true;
		try {
			const formData = new FormData();
			formData.append('file', file);
			const res = await fetch(`${proxyUrl}?_action=upload-image`, {
				method: 'POST',
				body: formData
			});
			if (res.ok) {
				const data = await res.json();
				const imageUrl = `${proxyUrl}?_action=serve-image&attachment_id=${data.id}`;
				insertAtCursor(`![image](${imageUrl})`);
				await saveDescription();
			}
		} finally {
			uploading = false;
		}
	}

	function insertAtCursor(text: string) {
		if (!textareaEl) {
			splashDescription += '\n' + text;
			return;
		}
		const start = textareaEl.selectionStart;
		const end = textareaEl.selectionEnd;
		splashDescription =
			splashDescription.substring(0, start) + text + splashDescription.substring(end);
		const newPos = start + text.length;
		requestAnimationFrame(() => {
			textareaEl?.setSelectionRange(newPos, newPos);
			textareaEl?.focus();
		});
	}

	function wrapSelection(before: string, after: string) {
		if (!textareaEl) return;
		const start = textareaEl.selectionStart;
		const end = textareaEl.selectionEnd;
		const selected = splashDescription.substring(start, end);
		const placeholder = selected || 'text';
		const replacement = before + placeholder + after;
		splashDescription =
			splashDescription.substring(0, start) + replacement + splashDescription.substring(end);
		requestAnimationFrame(() => {
			if (selected) {
				textareaEl?.setSelectionRange(
					start + before.length,
					start + before.length + selected.length
				);
			} else {
				textareaEl?.setSelectionRange(
					start + before.length,
					start + before.length + placeholder.length
				);
			}
			textareaEl?.focus();
		});
	}

	function insertLinePrefix(prefix: string) {
		if (!textareaEl) return;
		const start = textareaEl.selectionStart;
		const lineStart = splashDescription.lastIndexOf('\n', start - 1) + 1;
		splashDescription =
			splashDescription.substring(0, lineStart) + prefix + splashDescription.substring(lineStart);
		const newPos = start + prefix.length;
		requestAnimationFrame(() => {
			textareaEl?.setSelectionRange(newPos, newPos);
			textareaEl?.focus();
		});
	}

	function handlePaste(e: ClipboardEvent) {
		if (!e.clipboardData) return;
		const items = e.clipboardData.items;
		for (const item of items) {
			if (item.type.startsWith('image/')) {
				e.preventDefault();
				const file = item.getAsFile();
				if (file) uploadImage(file);
				return;
			}
		}
	}

	function handleFileInput(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files?.[0]) {
			uploadImage(input.files[0]);
			input.value = '';
		}
	}

	/** Auto-grow a textarea to fit its content */
	function autoGrow(el: HTMLTextAreaElement) {
		el.style.height = 'auto';
		el.style.height = Math.max(40, el.scrollHeight) + 'px';
	}

	/** Svelte action: auto-grow textarea on mount and on input */
	function autogrowAction(el: HTMLTextAreaElement) {
		autoGrow(el);
		const onInput = () => autoGrow(el);
		el.addEventListener('input', onInput);
		return {
			destroy() {
				el.removeEventListener('input', onInput);
			}
		};
	}

	const isSplash = $derived(node.node.display_mode === 'splash');
</script>

<div style="margin-left: {Math.min(node.depth, 3) * 16}px">
	<div
		class="bg-white rounded-lg shadow-sm border overflow-hidden
		{isSplash ? 'border-purple-200' : 'border-gray-200'}
		{node.depth > 0 ? 'border-l-4 ' + (isSplash ? 'border-l-purple-400' : depthColor) : ''}"
	>
		<!-- Parent breadcrumb for deep nesting -->
		{#if node.depth >= 3 && node.node.parent_urn}
			<div class="px-4 pt-2 pb-0">
				<span class="text-[10px] text-gray-400">
					<i class="fa-solid fa-turn-up fa-rotate-90 mr-1"></i>nested under {node.node.parent_urn
						.split(':')
						.pop()
						?.slice(0, 12)}
				</span>
			</div>
		{/if}

		<!-- Status line -->
		<div class="px-4 pt-2 text-[11px] {isSplash ? 'text-purple-400' : 'text-gray-400'}">
			{#if isSplash}
				<i class="fa-solid fa-display mr-1"></i>
			{/if}
			{statusLine}
		</div>

		<!-- Header -->
		<div
			class="px-4 py-3 {isSplash
				? 'border-b border-purple-100'
				: 'border-b border-gray-100'} flex items-start gap-3 group"
		>
			<span class="cursor-grab text-gray-300 group-hover:text-gray-400 mt-1" data-drag-handle>
				<i class="fa-solid fa-grip-vertical text-xs"></i>
			</span>

			<div class="flex-1 min-w-0 space-y-1">
				{#if $activeLanguageStore}
					{@const lang = $activeLanguageStore}
					<!-- Translation mode: show source readonly + editable translation side by side -->
					<div class="flex items-center gap-2">
						<input
							type="text"
							value={node.node.ref_id ?? ''}
							placeholder="Ref ID"
							class="w-24 text-xs font-mono bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors text-gray-500"
							onblur={(e) => saveField('ref_id', e.currentTarget.value || null)}
						/>
					</div>
					<div class="grid grid-cols-2 gap-3">
						<input
							type="text"
							value={node.node.name ?? ''}
							readonly
							class="text-sm font-medium bg-transparent border-0 border-b border-transparent py-0.5 text-gray-400 cursor-default"
						/>
						<input
							type="text"
							value={getTranslation(node.node.translations, lang, 'name')}
							placeholder={isSplash ? 'Translate title...' : 'Translate name...'}
							class="text-sm font-medium bg-transparent border-0 border-b border-transparent hover:border-blue-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors"
							onblur={(e) =>
								saveField(
									'translations',
									withTranslation(node.node.translations, lang, 'name', e.currentTarget.value)
								)}
						/>
					</div>
					{#if node.node.urn}
						<button
							type="button"
							class="inline-flex items-center gap-1 text-[10px] font-mono text-gray-300 hover:text-gray-500 transition-colors truncate max-w-full text-left group/urn"
							onclick={() => urnCopy.copy(node.node.urn ?? '')}
						>
							<i
								class="fa-solid {urnCopy.copied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"
							></i>
							{#if urnCopy.copied}
								<span class="text-green-500">Copied!</span>
							{:else}
								{node.node.urn}
							{/if}
						</button>
					{/if}

					{#if !isSplash}
						<!-- Description side-by-side -->
						<div class="grid grid-cols-2 gap-3">
							<textarea
								value={node.node.description ?? ''}
								readonly
								rows="3"
								use:autogrowAction
								class="w-full text-xs text-gray-300 bg-transparent border-0 border-b border-transparent resize-none py-0.5 cursor-default"
							></textarea>
							<textarea
								value={getTranslation(node.node.translations, lang, 'description')}
								placeholder="Translate description..."
								rows="3"
								use:autogrowAction
								class="w-full text-xs bg-transparent border-0 border-b border-transparent hover:border-blue-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
								onblur={(e) =>
									saveField(
										'translations',
										withTranslation(
											node.node.translations,
											lang,
											'description',
											e.currentTarget.value
										)
									)}
							></textarea>
						</div>
						{#if node.node.assessable}
							<!-- Typical evidence side-by-side -->
							<div class="grid grid-cols-2 gap-3">
								<textarea
									value={node.node.typical_evidence ?? ''}
									readonly
									rows="2"
									use:autogrowAction
									class="w-full text-xs text-gray-300 bg-transparent border-0 border-b border-transparent resize-none py-0.5 cursor-default"
								></textarea>
								<textarea
									value={getTranslation(node.node.translations, lang, 'typical_evidence')}
									placeholder="Translate typical evidence..."
									rows="2"
									use:autogrowAction
									class="w-full text-xs bg-transparent border-0 border-b border-transparent hover:border-blue-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
									onblur={(e) =>
										saveField(
											'translations',
											withTranslation(
												node.node.translations,
												lang,
												'typical_evidence',
												e.currentTarget.value
											)
										)}
								></textarea>
							</div>
						{/if}
					{/if}
				{:else}
					<!-- Normal (non-translation) mode -->
					<div class="flex items-center gap-2">
						<input
							type="text"
							value={node.node.ref_id ?? ''}
							placeholder="Ref ID"
							class="w-24 text-xs font-mono bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:{isSplash
								? 'border-purple-500'
								: 'border-blue-500'} px-0.5 py-0.5 outline-none focus-visible:ring-2 {isSplash
								? 'focus-visible:ring-purple-500/40'
								: 'focus-visible:ring-blue-500/40'} transition-colors text-gray-500"
							onblur={(e) => saveField('ref_id', e.currentTarget.value || null)}
						/>
						<div class="relative flex-1">
							<input
								type="text"
								value={node.node.name ?? ''}
								placeholder={isSplash
									? 'Splash screen title'
									: node.node.description
										? node.node.description.slice(0, 60) +
											(node.node.description.length > 60 ? '...' : '')
										: 'Node name'}
								class="w-full text-sm font-medium bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:{isSplash
									? 'border-purple-500'
									: 'border-blue-500'} px-0.5 py-0.5 outline-none focus-visible:ring-2 {isSplash
									? 'focus-visible:ring-purple-500/40'
									: 'focus-visible:ring-blue-500/40'} transition-colors"
								onblur={(e) => saveField('name', e.currentTarget.value || null)}
							/>
							{#if nameLength > 0}
								<span
									class="absolute right-0 top-0 text-[10px] {nameLength > 180
										? 'text-red-500 font-medium'
										: 'text-gray-300'}"
								>
									{nameLength}/200
								</span>
							{/if}
						</div>
					</div>
					{#if node.node.urn}
						<button
							type="button"
							class="inline-flex items-center gap-1 text-[10px] font-mono text-gray-300 hover:text-gray-500 transition-colors truncate max-w-full text-left group/urn"
							onclick={() => urnCopy.copy(node.node.urn ?? '')}
						>
							<i
								class="fa-solid {urnCopy.copied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"
							></i>
							{#if urnCopy.copied}
								<span class="text-green-500">Copied!</span>
							{:else}
								{node.node.urn}
							{/if}
						</button>
					{/if}
				{/if}
			</div>

			<!-- Right controls: Assessable checkbox, Display mode select, Delete -->
			<div class="flex items-center gap-2 shrink-0">
				{#if !isSplash}
					<label
						class="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer hover:text-gray-600 transition-colors"
						title="Whether this requirement is assessable by respondents"
					>
						<input
							type="checkbox"
							checked={node.node.assessable}
							onchange={(e) => saveField('assessable', e.currentTarget.checked)}
							class="w-4 h-4 rounded border-gray-300 cursor-pointer"
						/>
						Assessable
					</label>
				{/if}
				<select
					value={node.node.display_mode}
					onchange={(e) => saveField('display_mode', e.currentTarget.value)}
					class="text-xs bg-transparent border-b border-gray-200 focus:border-blue-500 outline-none"
					title="Display mode"
				>
					<option value="default">Default</option>
					<option value="splash">Splash</option>
				</select>
				<ConfirmAction
					onconfirm={() => builder.deleteNode(node.node.id)}
					confirmLabel="Delete"
					triggerClass="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 transition-all"
					confirmClass="text-xs text-red-600 font-medium px-2 py-0.5 rounded bg-red-50"
				/>
			</div>
		</div>

		<!-- Body: branches on display_mode -->
		{#if isSplash}
			<!-- Markdown editor body (ported from SplashScreenBlock) -->
			<div class="px-4 py-3">
				{#if $activeLanguageStore}
					<!-- Side-by-side translation mode -->
					<div class="grid grid-cols-2 gap-4">
						<!-- Source (read-only preview) -->
						<div>
							<span class="text-[10px] text-gray-400 uppercase tracking-wider mb-1 block"
								>Source</span
							>
							<div class="min-h-[120px] bg-gray-50 border border-gray-100 rounded-lg px-3 py-2">
								{#if splashDescription.trim()}
									<MarkdownRenderer content={splashDescription} />
								{:else}
									<p class="text-sm text-gray-300 italic">No source content.</p>
								{/if}
							</div>
						</div>
						<!-- Target (editable) -->
						<div>
							<span
								class="text-[10px] text-blue-600 uppercase tracking-wider font-medium mb-1 block"
							>
								{$activeLanguageStore.toUpperCase()}
							</span>
							<textarea
								bind:value={splashTransDescription}
								onblur={saveTransDescription}
								placeholder="Translate markdown content..."
								rows="6"
								class="w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2 outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-500/20 transition-colors resize-y font-mono"
							></textarea>
						</div>
					</div>
				{:else}
					<!-- Normal editing mode: toolbar + textarea or preview -->
					<div class="flex items-center gap-1 mb-2">
						<div class="flex rounded-lg border border-gray-200 overflow-hidden">
							<button
								class="px-2.5 py-1 text-xs font-medium transition-colors {splashMode === 'edit'
									? 'bg-purple-500 text-white'
									: 'bg-gray-50 text-gray-600 hover:bg-gray-100'}"
								onclick={() => (splashMode = 'edit')}
							>
								<i class="fa-solid fa-pen mr-1 text-[10px]"></i>Edit
							</button>
							<button
								class="px-2.5 py-1 text-xs font-medium border-l border-gray-200 transition-colors {splashMode ===
								'preview'
									? 'bg-purple-500 text-white'
									: 'bg-gray-50 text-gray-600 hover:bg-gray-100'}"
								onclick={() => (splashMode = 'preview')}
							>
								<i class="fa-solid fa-eye mr-1 text-[10px]"></i>Preview
							</button>
						</div>

						{#if splashMode === 'edit'}
							<div class="flex items-center gap-0.5 ml-2 border-l border-gray-200 pl-2">
								<button
									class="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
									onclick={() => wrapSelection('**', '**')}
									title="Bold"
								>
									<i class="fa-solid fa-bold text-xs"></i>
								</button>
								<button
									class="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
									onclick={() => wrapSelection('*', '*')}
									title="Italic"
								>
									<i class="fa-solid fa-italic text-xs"></i>
								</button>
								<button
									class="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
									onclick={() => insertLinePrefix('# ')}
									title="Heading"
								>
									<i class="fa-solid fa-heading text-xs"></i>
								</button>
								<button
									class="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
									onclick={() => insertLinePrefix('- ')}
									title="Bullet list"
								>
									<i class="fa-solid fa-list-ul text-xs"></i>
								</button>
								<button
									class="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
									onclick={() => insertLinePrefix('1. ')}
									title="Numbered list"
								>
									<i class="fa-solid fa-list-ol text-xs"></i>
								</button>
								<button
									class="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
									onclick={() => wrapSelection('[', '](url)')}
									title="Link"
								>
									<i class="fa-solid fa-link text-xs"></i>
								</button>
								<button
									class="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
									onclick={() =>
										insertAtCursor(
											'\n| Column 1 | Column 2 |\n|----------|----------|\n| Cell     | Cell     |\n'
										)}
									title="Table"
								>
									<i class="fa-solid fa-table text-xs"></i>
								</button>
								<button
									class="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
									onclick={() => fileInputEl?.click()}
									title="Insert image"
									disabled={uploading}
								>
									{#if uploading}
										<i class="fa-solid fa-spinner fa-spin text-xs"></i>
									{:else}
										<i class="fa-solid fa-image text-xs"></i>
									{/if}
								</button>
								<input
									type="file"
									accept="image/*"
									class="hidden"
									bind:this={fileInputEl}
									onchange={handleFileInput}
								/>
							</div>
						{/if}
					</div>

					<!-- Content area -->
					{#if splashMode === 'edit'}
						<textarea
							bind:value={splashDescription}
							bind:this={textareaEl}
							onpaste={handlePaste}
							onblur={saveDescription}
							placeholder="Write markdown content for your splash screen..."
							rows="6"
							class="w-full text-sm bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-500/20 transition-colors resize-y font-mono"
						></textarea>
					{:else}
						<div class="min-h-[120px] bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
							{#if splashDescription.trim()}
								<MarkdownRenderer content={splashDescription} />
							{:else}
								<p class="text-sm text-gray-400 italic">
									No content yet. Switch to Edit to add markdown.
								</p>
							{/if}
						</div>
					{/if}
				{/if}
			</div>
		{:else}
			<!-- Default (non-splash) body: description + typical_evidence -->
			{#if !$activeLanguageStore}
				<div class="px-4 pt-2 pb-0 space-y-1">
					<textarea
						value={node.node.description ?? ''}
						placeholder="Description (optional)"
						rows="3"
						use:autogrowAction
						class="w-full text-xs text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
						onblur={(e) => saveField('description', e.currentTarget.value || null)}
					></textarea>
					{#if node.node.assessable}
						<textarea
							value={node.node.typical_evidence ?? ''}
							placeholder="Typical evidence (optional)"
							rows="2"
							use:autogrowAction
							class="w-full text-xs text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
							onblur={(e) => saveField('typical_evidence', e.currentTarget.value || null)}
						></textarea>
					{/if}
				</div>
			{/if}

			<!-- Implementation groups (only shown for assessable nodes) -->
			{#if node.node.assessable && $frameworkStore.implementation_groups_definition && $frameworkStore.implementation_groups_definition.length > 0}
				<div class="px-4 py-2 border-b border-gray-100">
					<span class="text-xs text-gray-500 mr-2">Implementation groups:</span>
					{#each $frameworkStore.implementation_groups_definition as ig}
						{@const refId = (ig as Record<string, string>).ref_id}
						{@const selected = (node.node.implementation_groups ?? []).includes(refId)}
						<button
							type="button"
							class="text-xs px-2 py-0.5 rounded-full border mr-1 transition-colors {selected
								? 'bg-blue-100 border-blue-300 text-blue-700'
								: 'bg-gray-50 border-gray-200 text-gray-400 hover:border-gray-300'}"
							onclick={() => {
								const current = node.node.implementation_groups ?? [];
								const next = selected ? current.filter((g) => g !== refId) : [...current, refId];
								builder.updateNode(node.node.id, { implementation_groups: next });
							}}
						>
							{refId}
						</button>
					{/each}
				</div>
			{/if}
		{/if}

		<!-- CEL visibility expression (shared for all node types) -->
		<div class="px-4 py-2 border-t {isSplash ? 'border-purple-100' : 'border-gray-100'}">
			<label class="text-xs text-gray-500 block mb-1">
				Visibility expression (CEL)
				<span
					class="text-gray-400 ml-1"
					title="CEL expression that must evaluate to true for this requirement to be visible. Example: requirements[&quot;urn:...&quot;].score > 50"
					>&#9432;</span
				>
			</label>
			<input
				type="text"
				class="w-full text-xs px-2 py-1 border border-gray-200 rounded font-mono bg-gray-50 focus:bg-white focus:{isSplash
					? 'border-purple-300'
					: 'border-blue-300'} focus:outline-none"
				placeholder={'e.g. requirements["urn:..."].score > 50'}
				value={node.node.visibility_expression ?? ''}
				onblur={(e) => saveField('visibility_expression', e.currentTarget.value || null)}
			/>
		</div>

		<!-- Questions (only for assessable non-splash nodes) -->
		{#if node.node.assessable && !isSplash}
			<div class="px-4 py-3 space-y-1">
				{#each node.questions as bq, qIndex (bq.question.id)}
					<QuestionEditor
						question={bq.question}
						reqNodeId={node.node.id}
						{qIndex}
						siblingQuestions={allQuestions}
					/>
				{/each}

				<button
					type="button"
					class="w-full py-2 border-2 border-dashed border-gray-200 rounded-lg text-xs text-gray-400 hover:text-gray-600 hover:border-gray-300 transition-colors"
					onclick={() => builder.addQuestion(node.node.id)}
				>
					<i class="fa-solid fa-plus mr-1"></i>Add question
				</button>
			</div>
		{/if}

		<!-- Error display (shared) -->
		{#if $errorsStore.has(`node-${node.node.id}`)}
			<div class="px-4 py-2 bg-red-50 border-t border-red-200">
				<p class="text-xs text-red-600">{$errorsStore.get(`node-${node.node.id}`)}</p>
			</div>
		{/if}

		<!-- Add child button -->
		{#if node.node.urn}
			<AddNodeMenu
				parent={node.node.id}
				triggerLabel={'+ Add child'}
				triggerClass="w-full py-1 text-[11px] text-gray-300 hover:text-gray-500 transition-colors border-t border-gray-100"
			/>
		{/if}
	</div>

	<!-- Add sibling below button -->
	{#if parentId !== undefined}
		<AddNodeMenu
			parent={parentId}
			afterIndex={indexWithinParent}
			triggerLabel={'+ Add sibling below'}
			triggerClass="w-full py-1 text-[11px] text-gray-300 hover:text-gray-500 transition-colors"
		/>
	{/if}

	<!-- Recursive children -->
	{#if node.children.length > 0}
		<div class="space-y-3 mt-2">
			{#each node.children as child, childIndex (child.node.id)}
				<div
					class:opacity-50={childDrag.draggedIndex === childIndex}
					draggable="true"
					onmousedown={childDrag.recordMousedown}
					ondragstart={(e) => childDrag.handleDragStart(e, childIndex)}
					ondragover={childDrag.handleDragOver}
					ondrop={(e) => childDrag.handleDrop(e, childIndex)}
					ondragend={childDrag.handleDragEnd}
					role="listitem"
				>
					<svelte:self node={child} parentId={node.node.id} indexWithinParent={childIndex} />
				</div>
			{/each}
		</div>
	{/if}
</div>
