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
	<dd class="text-gray-700 whitespace-pre-line grid grid-cols-4">
		<i class="fa-solid fa-plus col-span-1 pt-1" aria-hidden="true"></i>
		<span class="col-span-2">
			<ul>
				{#each objects as object}
					<li>
						{object}
					</li>
				{/each}
			</ul>
		</span>
	</dd>
</div>
