<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';

	type ProcessedValue = string | number | boolean | null | Record<string, any> | Array<any>;

	interface Props {
		action: string;
		field: string;
		before: ProcessedValue;
		after: ProcessedValue;
	}

	let { action, field, before, after }: Props = $props();
</script>

<div class="grid grid-cols-[1fr_3fr]">
	<dt class="font-medium text-gray-900" data-testid="{field.replace('_', '-')}-field-title">
		{safeTranslate(field)}
	</dt>
	<dd class="text-gray-700 whitespace-pre-line grid grid-cols-4">
		{#if ['update', 'delete'].includes(action)}
			<span class={action === 'delete' ? 'col-span-4' : ''}>
				{before}
			</span>
		{/if}

		{#if action === 'update' || (action === 'create' && after !== 'None')}
			<i class="fa-solid fa-arrow-right col-span-1 pt-1" aria-hidden="true"></i>
			<span class={action === 'update' ? 'col-span-2' : 'col-span-3'}>
				{after}
			</span>
		{/if}
	</dd>
</div>
