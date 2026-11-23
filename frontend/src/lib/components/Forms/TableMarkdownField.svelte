<script lang="ts">
	import { untrack } from 'svelte';
	import MarkdownRenderer from '#lib/components/MarkdownRenderer.svelte';
	import { m } from '#paraglide/messages.js';

	interface Props {
		value: string;
		onSave: (value: string) => void;
		placeholder?: string;
		disabled?: boolean;
	}

	let {
		value = $bindable(),
		onSave,
		placeholder = m.markdownCTA(),
		disabled = false
	}: Props = $props();

	let isEditing = $state(false);
	let editValue = $state(value ?? '');
	let isDirty = $derived((editValue ?? '') !== (value ?? ''));
	let syncedValue = value ?? '';

	$effect(() => {
		const next = value ?? '';
		if (next === syncedValue) return;
		if ((untrack(() => editValue) ?? '') === syncedValue) editValue = next;
		syncedValue = next;
	});

	function startEdit() {
		if (disabled) return;
		isEditing = true;
	}

	function saveChanges() {
		value = editValue;
		onSave(editValue);
		isEditing = false;
	}

	function cancelEdit() {
		editValue = value;
		isEditing = false;
	}

	function preview() {
		isEditing = false;
	}
</script>

<div class="space-y-2">
	{#if isEditing}
		<!-- Edit Mode -->
		<textarea
			class="input w-full"
			rows="5"
			placeholder={m.markdownPlaceholder()}
			bind:value={editValue}
		></textarea>
		<div class="flex justify-end items-center">
			<div class="flex space-x-2">
				<button type="button" class="btn btn-sm preset-tonal-primary" onclick={preview}>
					<i class="fas fa-eye mr-1"></i>
					{m.preview()}
				</button>
				<button class="btn btn-sm preset-filled-primary-500" onclick={saveChanges} type="button">
					<i class="fa-solid fa-check mr-1"></i>
					{m.save()}
				</button>
				<button class="btn btn-sm preset-tonal" onclick={cancelEdit} type="button">
					<i class="fa-solid fa-xmark mr-1"></i>
					{m.cancel()}
				</button>
			</div>
		</div>
		<p class="text-xs text-surface-400-600">
			{m.markdownHelpText()}
		</p>
	{:else}
		<!-- Preview Mode -->
		<div
			class="prose prose-sm max-w-none p-3 border border-surface-300-700 rounded-md min-h-[120px] bg-surface-50-950 {disabled
				? ''
				: 'cursor-text'}"
			ondblclick={startEdit}
			role={disabled ? undefined : 'button'}
			tabindex={disabled ? -1 : 0}
			onkeydown={(e) => {
				if (e.key === 'Enter' || e.key === ' ') {
					e.preventDefault();
					startEdit();
				}
			}}
		>
			{#if editValue}
				<MarkdownRenderer content={editValue} />
			{:else}
				<p class="text-surface-600-400 italic">{disabled ? m.noObservation() : placeholder}</p>
			{/if}
		</div>
		{#if !disabled}
			<div class="flex justify-end items-center gap-2">
				{#if isDirty}
					<span class="text-xs italic text-warning-600-400">{m.unsavedChanges()}</span>
				{/if}
				<div class="flex space-x-2">
					<button type="button" class="btn btn-sm preset-tonal" onclick={startEdit}>
						<i class="fas fa-edit mr-1"></i>
						{m.edit()}
					</button>
					{#if isDirty}
						<button
							class="btn btn-sm preset-filled-primary-500"
							onclick={saveChanges}
							type="button"
						>
							<i class="fa-solid fa-check mr-1"></i>
							{m.save()}
						</button>
						<button class="btn btn-sm preset-tonal" onclick={cancelEdit} type="button">
							<i class="fa-solid fa-xmark mr-1"></i>
							{m.cancel()}
						</button>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</div>
