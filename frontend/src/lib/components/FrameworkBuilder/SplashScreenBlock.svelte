<script lang="ts">
	import { getBuilderContext, type BuilderRequirement } from './builder-state';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	interface Props {
		requirement: BuilderRequirement;
	}

	let { requirement }: Props = $props();

	const builder = getBuilderContext();
	const { errors: errorsStore } = builder;
	let confirmDelete = $state(false);
	let urnCopied = $state(false);
	let mode: 'edit' | 'preview' = $state('edit');
	let uploading = $state(false);
	let textareaEl: HTMLTextAreaElement | undefined = $state();
	let fileInputEl: HTMLInputElement | undefined = $state();

	let description = $state(requirement.node.description ?? '');

	async function saveField(field: string, value: unknown) {
		await builder.updateNode(requirement.node.id, { [field]: value });
	}

	async function saveDescription() {
		await builder.updateNode(requirement.node.id, { description: description || null });
	}

	// --- Markdown editing helpers (ported from policy editor) ---

	async function uploadImage(file: File) {
		uploading = true;
		try {
			const formData = new FormData();
			formData.append('file', file);
			const res = await fetch(
				`?_action=upload-image&node_id=${requirement.node.id}`,
				{ method: 'POST', body: formData }
			);
			if (res.ok) {
				const data = await res.json();
				const imageUrl = `?_action=serve-image&node_id=${requirement.node.id}&attachment_id=${data.id}`;
				insertAtCursor(`![image](${imageUrl})`);
				await saveDescription();
			}
		} finally {
			uploading = false;
		}
	}

	function insertAtCursor(text: string) {
		if (!textareaEl) {
			description += '\n' + text;
			return;
		}
		const start = textareaEl.selectionStart;
		const end = textareaEl.selectionEnd;
		description = description.substring(0, start) + text + description.substring(end);
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
		const selected = description.substring(start, end);
		const placeholder = selected || 'text';
		const replacement = before + placeholder + after;
		description = description.substring(0, start) + replacement + description.substring(end);
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
		const lineStart = description.lastIndexOf('\n', start - 1) + 1;
		description = description.substring(0, lineStart) + prefix + description.substring(lineStart);
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
</script>

<div
	class="bg-white rounded-lg shadow-sm border border-purple-200 border-l-4 border-l-purple-400 overflow-hidden"
>
	<!-- Header -->
	<div class="px-4 py-3 border-b border-purple-100 flex items-start gap-3 group">
		<span class="cursor-grab text-gray-300 group-hover:text-gray-400 mt-1">
			<i class="fa-solid fa-grip-vertical text-xs"></i>
		</span>
		<div class="flex-1 min-w-0 space-y-1">
			<div class="flex items-center gap-2">
				<span class="text-purple-500 text-xs" title="Splash screen">
					<i class="fa-solid fa-display text-sm"></i>
				</span>
				<input
					type="text"
					value={requirement.node.ref_id ?? ''}
					placeholder="Ref ID"
					class="w-24 text-xs font-mono bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-purple-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-purple-500/40 transition-colors text-gray-500"
					onblur={(e) => saveField('ref_id', e.currentTarget.value || null)}
				/>
				<input
					type="text"
					value={requirement.node.name ?? ''}
					placeholder="Splash screen title"
					class="flex-1 text-sm font-medium bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-purple-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-purple-500/40 transition-colors"
					onblur={(e) => saveField('name', e.currentTarget.value || null)}
				/>
			</div>
			{#if requirement.node.urn}
				<button
					type="button"
					class="inline-flex items-center gap-1 text-[10px] font-mono text-gray-300 hover:text-gray-500 transition-colors truncate max-w-full text-left group/urn"
					onclick={() => {
						navigator.clipboard.writeText(requirement.node.urn ?? '');
						urnCopied = true;
						setTimeout(() => (urnCopied = false), 1500);
					}}
				>
					<i
						class="fa-solid {urnCopied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"
					></i>
					{#if urnCopied}
						<span class="text-green-500">Copied!</span>
					{:else}
						{requirement.node.urn}
					{/if}
				</button>
			{/if}
		</div>

		<div class="flex items-center gap-1 shrink-0">
			{#if confirmDelete}
				<button
					type="button"
					class="text-xs text-red-600 font-medium px-2 py-0.5 rounded bg-red-50"
					onclick={() => {
						builder.deleteRequirement(requirement.node.id);
						confirmDelete = false;
					}}
				>
					Delete
				</button>
				<button
					type="button"
					class="text-xs text-gray-500 px-2 py-0.5"
					onclick={() => (confirmDelete = false)}
				>
					Cancel
				</button>
			{:else}
				<button
					type="button"
					class="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 transition-all"
					onclick={() => (confirmDelete = true)}
				>
					<i class="fa-solid fa-trash text-xs"></i>
				</button>
			{/if}
		</div>
	</div>

	<!-- Markdown editor -->
	<div class="px-4 py-3">
		<!-- Toolbar -->
		<div class="flex items-center gap-1 mb-2">
			<div class="flex rounded-lg border border-gray-200 overflow-hidden">
				<button
					class="px-2.5 py-1 text-xs font-medium transition-colors {mode === 'edit'
						? 'bg-purple-500 text-white'
						: 'bg-gray-50 text-gray-600 hover:bg-gray-100'}"
					onclick={() => (mode = 'edit')}
				>
					<i class="fa-solid fa-pen mr-1 text-[10px]"></i>Edit
				</button>
				<button
					class="px-2.5 py-1 text-xs font-medium border-l border-gray-200 transition-colors {mode ===
					'preview'
						? 'bg-purple-500 text-white'
						: 'bg-gray-50 text-gray-600 hover:bg-gray-100'}"
					onclick={() => (mode = 'preview')}
				>
					<i class="fa-solid fa-eye mr-1 text-[10px]"></i>Preview
				</button>
			</div>

			{#if mode === 'edit'}
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
		{#if mode === 'edit'}
			<textarea
				bind:value={description}
				bind:this={textareaEl}
				onpaste={handlePaste}
				onblur={saveDescription}
				placeholder="Write markdown content for your splash screen..."
				rows="6"
				class="w-full text-sm bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-500/20 transition-colors resize-y font-mono"
			></textarea>
		{:else}
			<div class="min-h-[120px] bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
				{#if description.trim()}
					<MarkdownRenderer content={description} />
				{:else}
					<p class="text-sm text-gray-400 italic">No content yet. Switch to Edit to add markdown.</p>
				{/if}
			</div>
		{/if}
	</div>

	{#if $errorsStore.has(`node-${requirement.node.id}`)}
		<div class="px-4 py-2 bg-red-50 border-t border-red-200">
			<p class="text-xs text-red-600">{$errorsStore.get(`node-${requirement.node.id}`)}</p>
		</div>
	{/if}
</div>
