<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { markdownToIsolatedHtml } from '$lib/utils/markdown';
	import SandboxedHtmlFrame from './SandboxedHtmlFrame.svelte';
	import SheetPreview from './SheetPreview.svelte';
	import { renderDocx } from './renderDocx';

	interface Props {
		endpoint: string;
		filename: string;
	}

	let { endpoint, filename }: Props = $props();

	const IMAGE = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'];
	const VIDEO = ['mp4', 'mov'];
	const PLAIN = ['txt', 'log', 'yaml', 'yml', 'toml', 'xml', 'eml'];
	const TEXT_MAX = 5_000_000;
	const BINARY_MAX = 10_000_000;
	const MAX_LINES = 5000;

	type Kind = 'image' | 'pdf' | 'video' | 'text' | 'md' | 'docx' | 'sheet' | 'none';
	type Status = 'loading' | 'ready' | 'missing' | 'tooLarge' | 'failed';

	let status: Status = $state('loading');
	let kind: Kind = $state('none');
	let blob: Blob | undefined = $state();
	let url: string | undefined = $state();
	let text = $state('');
	let truncated = $state(false);
	let html: { body: string; css: string } | undefined = $state();
	let markdownBody: string | undefined = $state();

	// Markdown is rendered text rather than a fixed-layout document, so it follows the
	// app theme (`.dark` on <html>); spreadsheets and docx keep the file's own colours.
	let isDark = $state(false);
	$effect(() => {
		const root = document.documentElement;
		const update = () => (isDark = root.classList.contains('dark'));
		update();
		const observer = new MutationObserver(update);
		observer.observe(root, { attributes: true, attributeFilter: ['class'] });
		return () => observer.disconnect();
	});

	const markdownCss = $derived(
		isDark
			? MARKDOWN_CSS('oklch(0.25 0.03 263)', '#e5e7eb', 'oklch(0.2 0.03 263)', '#3f3f46')
			: MARKDOWN_CSS('#fff', '#111', '#f3f4f6', '#d1d5db')
	);

	function kindOf(extension: string, type: string): Kind {
		if (IMAGE.includes(extension) || type.startsWith('image/')) return 'image';
		if (extension === 'pdf') return 'pdf';
		if (VIDEO.includes(extension)) return 'video';
		if (extension === 'md') return 'md';
		if (extension === 'json' || PLAIN.includes(extension)) return 'text';
		if (extension === 'docx') return 'docx';
		if (extension === 'xlsx' || extension === 'csv') return 'sheet';
		return 'none';
	}

	async function loadText(source: Blob, extension: string) {
		const decoded = (await source.text()).replace(/^\uFEFF/, '');
		if (decoded.slice(0, 8192).includes('\u0000')) {
			status = 'failed';
			return;
		}
		let content = decoded;
		if (extension === 'json') {
			try {
				content = JSON.stringify(JSON.parse(decoded), null, 2);
			} catch {
				content = decoded;
			}
		}
		const lines = content.split('\n');
		truncated = lines.length > MAX_LINES;
		text = truncated ? lines.slice(0, MAX_LINES).join('\n') : content;
		status = 'ready';
	}

	onMount(async () => {
		let response: Response;
		try {
			response = await fetch(endpoint);
		} catch {
			status = 'missing';
			return;
		}
		if (!response.ok) {
			status = 'missing';
			return;
		}

		blob = await response.blob();
		const extension = filename.split('.').pop()?.toLowerCase() ?? '';
		kind = kindOf(extension, blob.type);

		if (kind === 'none') {
			status = 'failed';
			return;
		}
		if (kind === 'image' || kind === 'pdf' || kind === 'video') {
			url = URL.createObjectURL(blob);
			status = 'ready';
			return;
		}
		if ((kind === 'text' || kind === 'md') && blob.size > TEXT_MAX) {
			status = 'tooLarge';
			return;
		}
		if ((kind === 'docx' || kind === 'sheet') && blob.size > BINARY_MAX) {
			status = 'tooLarge';
			return;
		}

		try {
			if (kind === 'text') await loadText(blob, extension);
			else if (kind === 'md') {
				markdownBody = markdownToIsolatedHtml(await blob.text());
				status = 'ready';
			} else if (kind === 'docx') {
				html = await renderDocx(blob);
				status = 'ready';
			} else status = 'ready';
		} catch {
			status = 'failed';
		}
	});

	onDestroy(() => {
		if (url) URL.revokeObjectURL(url);
	});

	function MARKDOWN_CSS(bg: string, fg: string, block: string, line: string) {
		return `body{margin:16px;background:${bg};font:14px/1.6 system-ui,sans-serif;color:${fg}}
table{border-collapse:collapse}td,th{border:1px solid ${line};padding:4px 8px}
blockquote{margin:0 0 0 4px;padding-left:12px;border-left:3px solid ${line}}
pre{background:${block};padding:8px;overflow:auto}code{font-family:ui-monospace,monospace}`;
	}
</script>

{#if status === 'loading'}
	<span data-testid="loading-field">{m.loading()}...</span>
{:else if status === 'missing'}
	<p class="text-error-500 font-bold text-center">{m.couldNotFindAttachmentMessage()}</p>
{:else if status === 'tooLarge'}
	<p class="font-bold text-sm text-center">{m.previewTooLarge()}</p>
{:else if status === 'failed'}
	<p class="font-bold text-sm text-center">{m.NoPreviewMessage()}</p>
{:else if kind === 'image'}
	<img src={url} alt={filename} />
{:else if kind === 'pdf'}
	<embed src={url} type="application/pdf" width="100%" height="600px" />
{:else if kind === 'video'}
	<!-- svelte-ignore a11y_media_has_caption -->
	<video
		src={url}
		controls
		preload="metadata"
		class="w-full max-h-[70vh]"
		onerror={() => (status = 'failed')}
	></video>
{:else if kind === 'text'}
	<pre
		class="text-xs overflow-auto max-h-[70vh] p-3 bg-surface-100-900 rounded border border-surface-200-800">{text}</pre>
	{#if truncated}
		<p class="text-sm text-surface-600-400">{m.previewTruncated()}</p>
	{/if}
{:else if kind === 'sheet' && blob}
	<SheetPreview
		{blob}
		kind={filename.toLowerCase().endsWith('.csv') ? 'csv' : 'xlsx'}
		title={filename}
	/>
{:else if markdownBody !== undefined}
	<SandboxedHtmlFrame body={markdownBody} css={markdownCss} title={filename} />
{:else if html}
	<SandboxedHtmlFrame body={html.body} css={html.css} title={filename} />
{/if}
