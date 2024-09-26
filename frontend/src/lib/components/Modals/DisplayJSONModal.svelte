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
	const cHeader = 'text-2xl font-bold';
</script>

{#if $modalStore[0]}
	{@const body = $modalStore[0].body}
	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>
		{#if body}
			<div data-testid="key-value">
				{#each Object.entries(JSON.parse(body)) as [key, value]}
					<div>
						<div data-testid="{key}-key" class="font-bold capitalize">{key}:</div>
						<div data-testid="{key}-value">{value}</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
