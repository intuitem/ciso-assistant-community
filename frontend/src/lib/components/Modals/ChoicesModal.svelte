<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { getModalStore, type ModalStore } from './stores';

	interface Props {
		parent: any;
		title?: string;
		message?: string;
		choices?: Choice[];
	}

	let { parent, title = 'Choices required', message = '', choices = [] }: Props = $props();

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	const modalStore: ModalStore = getModalStore();
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			{title}
		</header>
		<span>{safeTranslate(message)}</span>
		{#if choices && choices.length > 0}
			<div class="grid grid-cols-3 gap-x-8 gap-y-4">
				{#each choices as choice}
					<button class="badge bg-primary-50">{choice.name}</button>
				{/each}
			</div>
		{/if}
	</div>
{/if}
