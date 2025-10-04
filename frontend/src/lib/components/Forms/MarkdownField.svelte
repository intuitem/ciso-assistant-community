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
		field: string;
		helpText?: string | undefined;
		form: any;
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
		defaultMode = 'preview',
		...rest
	}: Props = $props();

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, field);

	let showPreview = $state(defaultMode === 'preview');

	run(() => {
		cachedValue = $value;
	});

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
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
				class="p-3 border border-surface-300 rounded-md min-h-[120px] overflow-auto max-h-[75dvh] bg-surface-50"
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
				{#if $value}
					<MarkdownRenderer content={$value} />
				{:else}
					<p class="text-gray-500 italic">{m.markdownCTA()}</p>
				{/if}
			</div>
		{:else}
			<textarea
				class="{'input ' + _class} max-h-[75dvh] {classesTextField($errors)}"
				data-testid="form-input-{field.replaceAll('_', '-')}"
				name={field}
				aria-invalid={$errors ? 'true' : undefined}
				oninput={(event) => {
					adaptTextAreaSize(event.target);
				}}
				bind:this={textareaElem}
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
			{m.markdownHelpText()}
		</p>
	{/if}
</div>
