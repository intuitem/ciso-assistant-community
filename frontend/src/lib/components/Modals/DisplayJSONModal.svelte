<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { getModalStore, type ModalStore } from './stores';

	const cBase = 'card bg-surface-50-950 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	const modalStore: ModalStore = getModalStore();

	function parseBody(body: unknown) {
		if (typeof body !== 'string') return null;

		try {
			const parsed = JSON.parse(body);
			return parsed && typeof parsed === 'object' ? parsed : null;
		} catch {
			return null;
		}
	}
</script>

{#if $modalStore[0]}
	{@const body = $modalStore[0].body}
	{@const parsedBody = parseBody(body)}

	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>

		{#if parsedBody}
			<div data-testid="key-value">
				{#each Object.entries(parsedBody) as [key, value]}
					<div>
						<div data-testid="{key}-key" class="font-bold">{safeTranslate(key)}:</div>
						<div data-testid="{key}-value">{safeTranslate(String(value))}</div>
					</div>
				{/each}
			</div>
		{:else if body}
			<div data-testid="raw-body">
				{safeTranslate(String(body))}
			</div>
		{/if}
	</div>
{/if}
