<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		action: string;
		field: string;
		objects: any;
	}

	let { action, field, objects }: Props = $props();
</script>

<div class="grid grid-cols-[1fr_3fr]">
	<dt class="font-medium text-gray-900" data-testid="{field.replace('_', '-')}-field-title">
		{safeTranslate(field)}
	</dt>
	<dd class="text-gray-700 whitespace-pre-line flex gap-2">
		<i class="fa-solid fa-plus pt-1" aria-hidden="true"></i>
		<span class="flex-1">
			<ul>
				{#if objects.length === 0}
					<li class="text-gray-500 italic">No items added</li>
				{:else}
					{#each objects as object, index (index)}
						<li>
							{object}
						</li>
					{/each}
				{/if}
			</ul>
		</span>
	</dd>
</div>
