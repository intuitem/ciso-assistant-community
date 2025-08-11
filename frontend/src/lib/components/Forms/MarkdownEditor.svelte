<script lang="ts">
	import { run } from 'svelte/legacy';
	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';
	import { marked } from 'marked';
	import sanitizeHtml from 'sanitize-html';

	interface Props {
		class?: string;
		label?: string | undefined;
		field: string;
		helpText?: string | undefined;
		form: any;
		cachedValue?: string;
		cacheLock?: CacheLock;
		hidden?: boolean;
		disabled?: boolean;
		rows?: number;
		cols?: number;
		[key: string]: any;
	}

	let {
		class: _class = '',
		label = $bindable(),
		field,
		helpText = undefined,
		form,
		cachedValue = $bindable(),
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x) => x
		},
		hidden = false,
		disabled = false,
		rows = 5,
		cols = 50,
		...rest
	}: Props = $props();

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, field);

	let showPreview = $state(false);
	let renderedMarkdown = $state('');

	run(() => {
		cachedValue = $value;
	});

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	$effect(() => {
		if (showPreview && $value) {
			let html = marked($value) as string;
			html = sanitizeHtml(html, {
				allowedTags: [
					'p',
					'blockquote',
					'h1',
					'h2',
					'h3',
					'h4',
					'h5',
					'h6',
					'ul',
					'ol',
					'li',
					'strong',
					'em',
					'a',
					'code',
					'pre',
					'table',
					'thead',
					'tbody',
					'tr',
					'th',
					'td',
					'img',
					'hr',
					'br',
					'input'
				],
				allowedAttributes: {
					a: ['href', 'name', 'target', 'rel'],
					img: ['src', 'alt', 'title', 'width', 'height', 'loading'],
					code: ['class'],
					input: ['type', 'checked', 'disabled'],
					li: ['class'],
					ul: ['class']
				},
				allowedSchemes: ['http', 'https'],
				transformTags: {
					a: sanitizeHtml.simpleTransform(
						'a',
						{ rel: 'noopener noreferrer', target: '_blank' },
						true
					)
				}
			});

			// Clean up excessive spacing
			html = html
				.replace(/>\s+</g, '><') // Remove whitespace between tags
				.replace(/\n\s*\n/g, '\n') // Remove double line breaks
				.replace(/<\/p>\s*<ul>/g, '</p><ul>') // Remove space between paragraphs and lists
				.replace(/<\/ul>\s*<p>/g, '</ul><p>') // Remove space between lists and paragraphs
				.replace(/<\/p>\s*<ol>/g, '</p><ol>') // Remove space between paragraphs and ordered lists
				.replace(/<\/ol>\s*<p>/g, '</ol><p>'); // Remove space between ordered lists and paragraphs

			renderedMarkdown = html;
		}
	});

	let classesTextField = $derived((errors: string[] | undefined) => (errors ? 'input-error' : ''));
	let classesDisabled = $derived((d: boolean) => (d ? 'opacity-50' : ''));
</script>

<div class={classesDisabled(disabled)}>
	{#if label !== undefined && !hidden}
		<div class="flex justify-between items-center">
			{#if $constraints?.required}
				<label class="text-sm font-semibold" for={field}
					>{label} <span class="text-red-500">*</span></label
				>
			{:else}
				<label class="text-sm font-semibold" for={field}>{label}</label>
			{/if}
			<div class="flex space-x-2">
				<button
					type="button"
					class="btn btn-sm {!showPreview ? 'variant-filled-primary' : 'variant-soft'}"
					onclick={() => (showPreview = false)}
				>
					<i class="fas fa-edit mr-1"></i>
					Edit
				</button>
				<button
					type="button"
					class="btn btn-sm {showPreview ? 'variant-filled-primary' : 'variant-soft'}"
					onclick={() => (showPreview = true)}
				>
					<i class="fas fa-eye mr-1"></i>
					Preview
				</button>
			</div>
		</div>
	{/if}
	{#if $errors}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div class="control">
		{#if showPreview}
			<div
				class="prose prose-sm max-w-none p-3 border border-surface-300 rounded-md min-h-[120px] bg-surface-50"
			>
				{@html renderedMarkdown || '<p class="text-gray-500 italic">No content to preview</p>'}
			</div>
		{:else}
			<textarea
				class="{'input ' + _class} {classesTextField($errors)}"
				data-testid="form-input-{field.replaceAll('_', '-')}"
				name={field}
				aria-invalid={$errors ? 'true' : undefined}
				placeholder="You can use markdown formatting here..."
				bind:value={$value}
				{...$constraints}
				{...rest}
				{rows}
				{cols}
				{disabled}
			></textarea>
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
	{#if !showPreview}
		<p class="text-xs text-gray-400 mt-1">
			Supports markdown: **bold**, *italic*, `code`, [links](url), lists, etc.
		</p>
	{/if}
</div>
