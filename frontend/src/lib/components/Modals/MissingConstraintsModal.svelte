<script lang="ts">
	// Props
	/** Exposes parent props to this component. */
	// export let parent: any;

	// Stores
	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';

	const modalStore: ModalStore = getModalStore();

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold text-red-600 animate-pulse';
</script>

{#if $modalStore[0]}
	{@const value = $modalStore[0].value}
	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			<i class="fa-solid fa-triangle-exclamation"></i>{$modalStore[0].title ?? '(title missing)'}
		</header>
		<div>
			{#if value}
				Some mandatory objects for {$modalStore[0].body} are not created or imported yet:
				{#each value as key}
					<li class="font-bold">{key}</li>
				{/each}
				Please add them before proceeding.
			{/if}
		</div>
	</div>
{/if}
