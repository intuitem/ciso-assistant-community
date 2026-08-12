<script lang="ts">
	import { run } from 'svelte/legacy';
	import { formFieldProxy } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	import { m } from '$paraglide/messages';

	interface Props {
		class?: string;
		label?: string | undefined;
		field?: string;
		helpText?: string | undefined;
		form?: any;
		value?: string;
		cachedValue?: string;
		cacheLock?: CacheLock;
		hidden?: boolean;
		disabled?: boolean;
		rows?: number;
		cols?: number;
		defaultMode?: 'preview' | 'edit';
		[key: string]: any;
	}

	let {
		class: _class = '',
		label = $bindable(),
		field = '',
		helpText = undefined,
		form = undefined,
		value = $bindable(''),
		cachedValue = $bindable(),
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x) => x
		},
		hidden = false,
		disabled = false,
		rows = 5,
		cols = 50,
		defaultMode = 'preview',
		...rest
	}: Props = $props();

	label = label ?? field;

	// Form-coupled (sveltekit-superforms) vs standalone (plain bind:value).
	// Picking one path at mount keeps the template simple.
	const formCoupled = !!form;
	const proxy = formCoupled ? formFieldProxy(form, field) : null;
	const proxyValue = proxy?.value;
	const proxyErrors = proxy?.errors;
	const proxyConstraints = proxy?.constraints;

	let showPreview = $state(defaultMode === 'preview');

	run(() => {
		if (formCoupled && proxyValue) cachedValue = $proxyValue;
	});

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult && formCoupled && proxyValue) $proxyValue = cacheResult;
	});

	let classesTextField = $derived((errors: string[] | undefined) => (errors ? 'input-error' : ''));
	let classesDisabled = $derived((d: boolean) => (d ? 'opacity-50' : ''));

	function adaptTextAreaSize(textArea: HTMLTextAreaElement) {
		textArea.style.height = 'auto';
		textArea.style.height = textArea.scrollHeight + 'px';
	}

	let textareaElem: HTMLTextAreaElement | null = $state(null);

	$effect(() => {
		if (textareaElem) {
			adaptTextAreaSize(textareaElem);
		}
	});

	let currentValue = $derived(formCoupled && proxyValue ? $proxyValue : value);
	let currentErrors = $derived(formCoupled && proxyErrors ? $proxyErrors : undefined);
	let currentConstraints = $derived(
		formCoupled && proxyConstraints ? $proxyConstraints : undefined
	);

	// --- Formatting toolbar helpers -------------------------------------------
	function setValue(v: string) {
		if (formCoupled && proxyValue) $proxyValue = v;
		else value = v;
	}

	function restore(el: HTMLTextAreaElement, start: number, end: number) {
		requestAnimationFrame(() => {
			el.focus();
			el.setSelectionRange(start, end);
			adaptTextAreaSize(el);
		});
	}

	function surround(before: string, after: string = before) {
		const el = textareaElem;
		if (!el) return;
		const s = el.selectionStart;
		const e = el.selectionEnd;
		const val = currentValue ?? '';
		const selected = val.slice(s, e) || 'text';
		setValue(val.slice(0, s) + before + selected + after + val.slice(e));
		restore(el, s + before.length, s + before.length + selected.length);
	}

	function linePrefix(prefix: string) {
		const el = textareaElem;
		if (!el) return;
		const s = el.selectionStart;
		const val = currentValue ?? '';
		const lineStart = val.lastIndexOf('\n', s - 1) + 1;
		setValue(val.slice(0, lineStart) + prefix + val.slice(lineStart));
		restore(el, s + prefix.length, s + prefix.length);
	}

	function insertText(text: string) {
		const el = textareaElem;
		const val = currentValue ?? '';
		if (!el) {
			setValue(val + text);
			return;
		}
		const s = el.selectionStart;
		const e = el.selectionEnd;
		setValue(val.slice(0, s) + text + val.slice(e));
		restore(el, s + text.length, s + text.length);
	}

	const TOOLBAR = [
		{ icon: 'fa-bold', label: () => m.bold(), action: () => surround('**') },
		{ icon: 'fa-italic', label: () => m.italic(), action: () => surround('*') },
		{ icon: 'fa-heading', label: () => m.formatHeading(), action: () => linePrefix('## ') },
		{ icon: 'fa-list-ul', label: () => m.bulletList(), action: () => linePrefix('- ') },
		{ icon: 'fa-list-ol', label: () => m.numberedList(), action: () => linePrefix('1. ') },
		{ icon: 'fa-quote-right', label: () => m.quote(), action: () => linePrefix('> ') },
		{ icon: 'fa-code', label: () => m.code(), action: () => surround('`') },
		{ icon: 'fa-link', label: () => m.insertLink(), action: () => surround('[', '](url)') },
		{
			icon: 'fa-table',
			label: () => m.insertTable(),
			action: () => insertText('\n| Column 1 | Column 2 |\n| --- | --- |\n| Cell | Cell |\n')
		}
	];
</script>

<div class={classesDisabled(disabled)}>
	{#if label !== undefined && !hidden && label !== ''}
		<div class="flex justify-between items-center">
			{#if currentConstraints?.required}
				<label class="text-sm font-semibold" for={field}
					>{label} <span class="text-red-500">*</span></label
				>
			{:else}
				<label class="text-sm font-semibold" for={field}>{label}</label>
			{/if}
			<div class="flex space-x-2">
				<button
					type="button"
					data-testid="markdown-edit-btn-{field}"
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
	{#if currentErrors}
		<div>
			{#each currentErrors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	{#if !showPreview && !disabled}
		<div class="mb-1 flex flex-wrap gap-1">
			{#each TOOLBAR as btn (btn.icon)}
				<button
					type="button"
					class="btn btn-sm variant-soft px-2"
					title={btn.label()}
					aria-label={btn.label()}
					onclick={btn.action}
				>
					<i class="fa-solid {btn.icon} text-xs"></i>
				</button>
			{/each}
		</div>
	{/if}
	<div class="control">
		{#if showPreview}
			{#if formCoupled}
				<input type="hidden" name={field} value={currentValue} />
			{/if}
			<div
				class="p-3 border border-surface-300-700 rounded-md min-h-[120px] overflow-auto max-h-[75dvh] bg-surface-50-950"
				ondblclick={() => !disabled && (showPreview = false)}
				role="button"
				tabindex="0"
				style="cursor: {disabled ? 'default' : 'text'}; min-width: {cols}ch;"
				onkeydown={(e) => {
					if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
						e.preventDefault();
						showPreview = false;
					}
				}}
			>
				{#if currentValue}
					<MarkdownRenderer content={currentValue} />
				{:else}
					<p class="text-surface-600-400 italic">{m.markdownCTA()}</p>
				{/if}
			</div>
		{:else if formCoupled && proxyValue}
			<textarea
				class="{'input ' + _class} max-h-[75dvh] {classesTextField(currentErrors)}"
				data-testid="form-input-{field.replaceAll('_', '-')}"
				name={field}
				aria-invalid={currentErrors ? 'true' : undefined}
				oninput={(event) => {
					adaptTextAreaSize(event.target);
				}}
				bind:this={textareaElem}
				bind:value={$proxyValue}
				{...currentConstraints}
				{...rest}
				{rows}
				{cols}
				{disabled}
			></textarea>
		{:else}
			<textarea
				class="{'input ' + _class} max-h-[75dvh]"
				oninput={(event) => {
					adaptTextAreaSize(event.target);
				}}
				bind:this={textareaElem}
				bind:value
				{...rest}
				{rows}
				{cols}
				{disabled}
			></textarea>
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-surface-600-400">{helpText}</p>
	{/if}
	{#if !showPreview}
		<p class="text-xs text-surface-400-600 mt-1">
			{m.markdownHelpText()}
		</p>
	{/if}
</div>
