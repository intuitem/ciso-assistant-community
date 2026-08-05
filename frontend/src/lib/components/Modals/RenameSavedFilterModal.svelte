<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		parent: any;
		initialName: string;
		onRenamed: (name: string) => void;
	}

	let { parent, initialName, onRenamed }: Props = $props();

	let name = $state(initialName);
	let isSubmitting = $state(false);
	let errorMsg = $state<string | null>(null);

	async function handleSubmit() {
		if (!name.trim()) return;
		isSubmitting = true;
		errorMsg = null;
		try {
			onRenamed(name.trim());
			parent.onClose();
		} finally {
			isSubmitting = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div class="card bg-surface-50-950 p-4 w-modal shadow-xl space-y-4">
		<div class="flex items-center justify-between">
			<header class="text-2xl font-bold">{$modalStore[0].title ?? m.rename()}</header>
			<button
				type="button"
				aria-label={m.close()}
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</div>

		<input
			type="text"
			class="input w-full"
			bind:value={name}
			placeholder={m.name()}
			onkeydown={(e) => e.key === 'Enter' && handleSubmit()}
		/>

		{#if errorMsg}
			<p class="text-error-500 text-sm">{errorMsg}</p>
		{/if}

		<div class="flex justify-end gap-2">
			<button type="button" class="btn preset-tonal" onclick={parent.onClose}>
				{m.cancel()}
			</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				disabled={isSubmitting || !name.trim()}
				onclick={handleSubmit}
			>
				{m.save()}
			</button>
		</div>
	</div>
{/if}
