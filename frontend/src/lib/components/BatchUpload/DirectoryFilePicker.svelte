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
	<div class="inline-flex rounded-md border border-gray-200 p-0.5 bg-gray-50 text-sm">
		<button
			type="button"
			class="px-3 py-1 rounded transition-colors {mode === 'files'
				? 'bg-white text-gray-900 shadow-sm'
				: 'text-gray-600 hover:text-gray-900'}"
			onclick={() => (mode = 'files')}
			{disabled}
		>
			<i class="fa-solid fa-file mr-1.5"></i>{m.files()}
		</button>
		<button
			type="button"
			class="px-3 py-1 rounded transition-colors {mode === 'directory'
				? 'bg-white text-gray-900 shadow-sm'
				: 'text-gray-600 hover:text-gray-900'}"
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
			? 'opacity-60 cursor-not-allowed border-gray-200 bg-gray-50'
			: dragOver
				? 'border-indigo-500 bg-indigo-50'
				: 'border-gray-300 bg-gray-50 hover:border-indigo-400 hover:bg-indigo-50/40 cursor-pointer'}"
	>
		<i
			class="fa-solid {mode === 'files'
				? 'fa-file-arrow-up'
				: 'fa-folder-tree'} text-2xl text-gray-400"
		></i>
		<span class="text-sm font-medium text-gray-700">
			{mode === 'files' ? m.clickToPickFiles() : m.clickToPickDirectory()}
		</span>
		{#if mode === 'directory'}
			<span class="text-xs text-gray-500">{m.directoryPickerHelp()}</span>
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
