<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { FileEntry } from './types';

	interface Props {
		entries: FileEntry[];
		disabled?: boolean;
	}

	let { entries = $bindable([]), disabled = false }: Props = $props();

	let mode = $state<'files' | 'directory'>('files');
	let dragOver = $state(false);

	const filesInputId = 'bup-files-input';
	const dirInputId = 'bup-dir-input';

	function makeId() {
		return `f_${Math.random().toString(36).slice(2, 10)}_${Date.now().toString(36)}`;
	}

	function ingest(fileList: FileList | null) {
		if (!fileList) return;
		const additions: FileEntry[] = [];
		const seen = new Set(
			entries.map((e) => `${e.relPath}::${e.name}::${e.size}::${e.file.lastModified}`)
		);
		for (let i = 0; i < fileList.length; i++) {
			const f = fileList[i];
			const relPath = (f as File & { webkitRelativePath?: string }).webkitRelativePath || '';
			const key = `${relPath}::${f.name}::${f.size}::${f.lastModified}`;
			if (seen.has(key)) continue;
			seen.add(key);
			additions.push({
				id: makeId(),
				field: '',
				file: f,
				name: f.name,
				relPath,
				size: f.size,
				status: 'pending'
			});
		}
		entries = [...entries, ...additions];
	}

	function onFilesChange(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		ingest(input.files);
		input.value = '';
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		if (disabled) return;
		ingest(e.dataTransfer?.files ?? null);
	}

	function onDragOver(e: DragEvent) {
		e.preventDefault();
		if (!disabled) dragOver = true;
	}

	function onDragLeave() {
		dragOver = false;
	}
</script>

<div class="space-y-2">
	<!-- Mode toggle: low-emphasis segmented control so it doesn't fight the dropzone for attention -->
	<div class="inline-flex rounded-md border border-surface-200-800 p-0.5 bg-surface-50-950 text-sm">
		<button
			type="button"
			class="px-3 py-1 rounded transition-colors {mode === 'files'
				? 'bg-surface-50-950 text-surface-900-100 shadow-sm'
				: 'text-surface-600-400 hover:text-surface-900-100'}"
			onclick={() => (mode = 'files')}
			{disabled}
		>
			<i class="fa-solid fa-file mr-1.5"></i>{m.files()}
		</button>
		<button
			type="button"
			class="px-3 py-1 rounded transition-colors {mode === 'directory'
				? 'bg-surface-50-950 text-surface-900-100 shadow-sm'
				: 'text-surface-600-400 hover:text-surface-900-100'}"
			onclick={() => (mode = 'directory')}
			{disabled}
		>
			<i class="fa-solid fa-folder-tree mr-1.5"></i>{m.directory()}
		</button>
	</div>

	<!-- Styled drop-zone label drives the hidden native input -->
	<label
		for={mode === 'files' ? filesInputId : dirInputId}
		ondrop={onDrop}
		ondragover={onDragOver}
		ondragleave={onDragLeave}
		role="button"
		tabindex={disabled ? -1 : 0}
		class="flex flex-col items-center justify-center gap-1.5 px-4 py-6 border-2 border-dashed rounded-lg transition-colors
			{disabled
			? 'opacity-60 cursor-not-allowed border-surface-200-800 bg-surface-50-950'
			: dragOver
				? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30'
				: 'border-surface-300-700 bg-surface-50-950 hover:border-indigo-400 hover:bg-indigo-50/40 dark:hover:bg-indigo-900/20 cursor-pointer'}"
	>
		<i
			class="fa-solid {mode === 'files'
				? 'fa-file-arrow-up'
				: 'fa-folder-tree'} text-2xl text-surface-500"
		></i>
		<span class="text-sm font-medium text-surface-700-300">
			{mode === 'files' ? m.clickToPickFiles() : m.clickToPickDirectory()}
		</span>
		{#if mode === 'directory'}
			<span class="text-xs text-surface-600-400">{m.directoryPickerHelp()}</span>
		{/if}
	</label>

	<!-- Hidden native inputs (visually hidden but accessible/focusable through the label) -->
	<input
		id={filesInputId}
		type="file"
		multiple
		onchange={onFilesChange}
		{disabled}
		class="sr-only"
	/>
	<input
		id={dirInputId}
		type="file"
		multiple
		webkitdirectory
		directory
		onchange={onFilesChange}
		{disabled}
		class="sr-only"
	/>
</div>
