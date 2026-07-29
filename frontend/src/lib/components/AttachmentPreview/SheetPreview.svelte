<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import SpreadsheetWorker from './spreadsheet.worker?worker';
	import SandboxedHtmlFrame from './SandboxedHtmlFrame.svelte';
	import { parseCsv } from './parseCsv';
	import { renderSheet } from './renderSheet';
	import type { SheetModel, WorkerResponse } from './types';

	interface Props {
		blob: Blob;
		kind: 'xlsx' | 'csv';
		title: string;
	}

	let { blob, kind, title }: Props = $props();

	let model: SheetModel | undefined = $state();
	let failed = $state(false);
	let active = $state(0);

	const sheet = $derived(model?.sheets[active]);
	const rendered = $derived(sheet ? renderSheet(sheet) : undefined);

	onMount(() => {
		if (kind === 'csv') {
			blob
				.arrayBuffer()
				.then((buffer) => (model = parseCsv(buffer)))
				.catch(() => (failed = true));
			return;
		}
		const worker = new SpreadsheetWorker();
		worker.onmessage = ({ data }: MessageEvent<WorkerResponse>) => {
			if (data.ok && data.model.sheets.length) model = data.model;
			else failed = true;
			worker.terminate();
		};
		worker.onerror = () => {
			failed = true;
			worker.terminate();
		};
		blob.arrayBuffer().then(
			(buffer) => worker.postMessage({ buffer }, [buffer]),
			() => {
				failed = true;
				worker.terminate();
			}
		);
		return () => worker.terminate();
	});
</script>

{#if failed}
	<p class="font-bold text-sm text-center">{m.NoPreviewMessage()}</p>
{:else if model && sheet && rendered}
	{#if model.sheets.length > 1}
		<div class="flex flex-wrap gap-1" role="tablist">
			{#each model.sheets as tab, index}
				<button
					type="button"
					role="tab"
					aria-selected={index === active}
					class="btn btn-sm {index === active
						? 'preset-filled-primary-500'
						: 'preset-tonal-surface'}"
					onclick={() => (active = index)}
				>
					{tab.name}
				</button>
			{/each}
		</div>
	{/if}
	<SandboxedHtmlFrame body={rendered.body} css={rendered.css} title={`${title} — ${sheet.name}`} />
	{#if sheet.truncated || model.omittedSheets > 0}
		<p class="text-sm text-surface-600-400">{m.previewTruncated()}</p>
	{/if}
{:else}
	<span data-testid="loading-field">{m.loading()}...</span>
{/if}
