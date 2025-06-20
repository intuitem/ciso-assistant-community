<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { getModalStore, type ModalStore } from './stores';

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	const modalStore: ModalStore = getModalStore();
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
						<div data-testid="{key}-key" class="font-bold">{safeTranslate(key)}:</div>
						<div data-testid="{key}-value">{safeTranslate(value)}</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
