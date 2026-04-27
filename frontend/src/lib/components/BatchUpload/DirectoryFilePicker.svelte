<script lang="ts">
	import type { FileEntry } from './types';

	interface Props {
		entries: FileEntry[];
		disabled?: boolean;
	}

	let { entries = $bindable([]), disabled = false }: Props = $props();

	let mode = $state<'files' | 'directory'>('files');
	let fileInput = $state<HTMLInputElement | null>(null);
	let dirInput = $state<HTMLInputElement | null>(null);

	function makeId() {
		return `f_${Math.random().toString(36).slice(2, 10)}_${Date.now().toString(36)}`;
	}

	function ingest(fileList: FileList | null) {
		if (!fileList) return;
		const additions: FileEntry[] = [];
		const seen = new Set(entries.map((e) => `${e.relPath}::${e.name}::${e.size}`));
		for (let i = 0; i < fileList.length; i++) {
			const f = fileList[i];
			// File.webkitRelativePath is set when the input has webkitdirectory
			const relPath = (f as File & { webkitRelativePath?: string }).webkitRelativePath || '';
			const key = `${relPath}::${f.name}::${f.size}`;
			if (seen.has(key)) continue;
			seen.add(key);
			additions.push({
				id: makeId(),
				field: '', // assigned just before submit (file_0, file_1, …)
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
		input.value = ''; // allow re-picking the same file
	}

	function clearAll() {
		entries = [];
	}

	function removeEntry(id: string) {
		entries = entries.filter((e) => e.id !== id);
	}
</script>

<div class="space-y-3">
	<div class="flex gap-2">
		<button
			type="button"
			class="btn {mode === 'files' ? 'preset-filled' : 'preset-outlined'}"
			onclick={() => (mode = 'files')}
			{disabled}
		>
			<i class="fa-solid fa-file mr-2"></i>Files
		</button>
		<button
			type="button"
			class="btn {mode === 'directory' ? 'preset-filled' : 'preset-outlined'}"
			onclick={() => (mode = 'directory')}
			{disabled}
		>
			<i class="fa-solid fa-folder-tree mr-2"></i>Directory
		</button>
	</div>

	{#if mode === 'files'}
		<input
			bind:this={fileInput}
			type="file"
			multiple
			onchange={onFilesChange}
			{disabled}
			class="block w-full text-sm file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-indigo-600 file:text-white file:cursor-pointer hover:file:bg-indigo-500"
		/>
	{:else}
		<!-- webkitdirectory + directory enable directory selection on Chromium/Firefox/Edge/Safari TP -->
		<input
			bind:this={dirInput}
			type="file"
			multiple
			webkitdirectory
			directory
			onchange={onFilesChange}
			{disabled}
			class="block w-full text-sm file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-indigo-600 file:text-white file:cursor-pointer hover:file:bg-indigo-500"
		/>
		<p class="text-xs text-gray-500">
			Select a folder; the browser sends every file in it (including subfolders).
		</p>
	{/if}

	{#if entries.length > 0}
		<div class="flex justify-between items-center text-sm">
			<span class="text-gray-700">{entries.length} file(s) queued</span>
			<button type="button" class="btn-sm preset-outlined" onclick={clearAll} {disabled}>
				<i class="fa-solid fa-broom mr-1"></i>Clear
			</button>
		</div>
	{/if}
</div>
