<script lang="ts">
  import { safeTranslate } from '$lib/utils/i18n';

  type ProcessedValue = string | number | boolean | null | Record<string, any> | Array<any>;

  export let field: string;
  export let before: ProcessedValue;
  export let after: ProcessedValue;
</script>

<div class="px-4 grid grid-cols-6">
  <dt
    class="font-medium text-gray-900"
    data-testid="{field.replace('_', '-')}-field-title"
  >
    {safeTranslate(field)}
  </dt>
  <dd class="px-2 text-gray-700 col-span-2 whitespace-pre-line">
      <span>
        {before}
      </span>
  </dd>
  <i class="fa-solid fa-arrow-right my-auto" />
  <dd class="px-2 text-gray-700 col-span-2 whitespace-pre-line">
      <span>
        {after}
      </span>
  </dd>
</div>
