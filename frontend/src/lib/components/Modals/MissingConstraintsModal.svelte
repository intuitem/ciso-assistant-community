<script lang="ts">
	// Props
	/** Exposes parent props to this component. */
	// export let parent: any;

	// Stores
	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import * as m from '$paraglide/messages';
	import { localItems, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	const modalStore: ModalStore = getModalStore();

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold text-red-600 animate-pulse';
</script>

{#if $modalStore[0]}
	{@const value = $modalStore[0].value}
	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			<i class="fa-solid fa-triangle-exclamation" />
			{$modalStore[0].title ?? '(title missing)'}
		</header>
		<div>
			{#if value}
				{m.missingMandatoyObjects1({ model: $modalStore[0].body })}:
				{#each value as key}
					<li class="font-bold">{localItems()[toCamelCase(key)]}</li>
				{/each}
				{m.missingMandatoyObjects2()}.
			{/if}
		</div>
	</div>
{/if}
