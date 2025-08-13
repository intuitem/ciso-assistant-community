<script lang="ts">
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	interface Props {
		value: string;
		onSave: (value: string) => void;
		placeholder?: string;
	}

	let {
		value = $bindable(),
		onSave,
		placeholder = 'Double-click to add content...'
	}: Props = $props();

	let isEditing = $state(false);
	let editValue = $state(value);

	function startEdit() {
		isEditing = true;
		editValue = value;
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
</script>

<div class="space-y-2">
	{#if isEditing}
		<!-- Edit Mode -->
		<textarea
			class="input w-full"
			rows="5"
			placeholder="You can use markdown formatting here..."
			bind:value={editValue}
		></textarea>
		<div class="flex justify-between items-center">
			<button
				type="button"
				class="btn btn-sm variant-filled-primary"
				onclick={() => (isEditing = false)}
			>
				<i class="fas fa-eye mr-1"></i>
				Preview
			</button>
			<div class="flex space-x-2">
				<button class="btn btn-sm variant-filled-success" onclick={saveChanges} type="button">
					<i class="fa-solid fa-check mr-1"></i>
					Save
				</button>
				<button class="btn btn-sm variant-filled-error" onclick={cancelEdit} type="button">
					<i class="fa-solid fa-xmark mr-1"></i>
					Cancel
				</button>
			</div>
		</div>
		<p class="text-xs text-gray-400">
			Supports markdown: **bold**, *italic*, `code`, [links](url), lists, etc.
		</p>
	{:else}
		<!-- Preview Mode -->
		<div
			class="prose prose-sm max-w-none p-3 border border-surface-300 rounded-md min-h-[120px] bg-surface-50 cursor-text"
			ondblclick={startEdit}
			role="button"
			tabindex="0"
			onkeydown={(e) => {
				if (e.key === 'Enter' || e.key === ' ') {
					e.preventDefault();
					startEdit();
				}
			}}
		>
			{#if value}
				<MarkdownRenderer content={value} />
			{:else}
				<p class="text-gray-500 italic">{placeholder}</p>
			{/if}
		</div>
		<div class="flex justify-between items-center">
			<button type="button" class="btn btn-sm variant-soft" onclick={startEdit}>
				<i class="fas fa-edit mr-1"></i>
				Edit
			</button>
		</div>
	{/if}
</div>
