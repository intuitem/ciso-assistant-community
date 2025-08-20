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

<div class="px-4 grid grid-cols-6">
	<dt class="font-medium text-gray-900" data-testid="{field.replace('_', '-')}-field-title">
		{safeTranslate(field)}
	</dt>
	<dd class="px-2 text-gray-700 col-span-2 whitespace-pre-line">
    {#if action === "update" || before !== "None"}
		<span>
			{before}
		</span>
    {/if}
	</dd>
  {#if action === "update" || after !== "None"}
    <i class="fa-solid fa-arrow-right my-auto"></i>
    <dd class="px-2 text-gray-700 col-span-2 whitespace-pre-line">
      <span>
        {after}
      </span>
    </dd>
  {/if}
</div>
