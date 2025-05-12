<script lang="ts">
  import { safeTranslate } from '$lib/utils/i18n';

  type ProcessedValue = string | number | boolean | null | Record<string, any> | Array<any>;

  export let field: string;
  export let before: ProcessedValue;
  export let after: ProcessedValue;
</script>

<div class="px-4 grid grid-cols-6 gap-4 even:bg-gray-50">
  <dt
    class="font-medium text-gray-900"
    data-testid="{field.replace('_', '-')}-field-title"
  >
    {safeTranslate(field)}
  </dt>
  <dd class="text-gray-700 col-span-2">
    <ul>
      <li
        class="list-none whitespace-pre-line"
        data-testid={!(before instanceof Array)
          ? field.replace('_', '-') + '-before-value'
          : null}
      >
      {before}
      </li>
    </ul>
  </dd>
  <i class="fa-solid fa-arrow-right" />
  <dd class="text-gray-700 col-span-2">
    <ul>
      <li
        class="list-none whitespace-pre-line"
        data-testid={!(before instanceof Array)
          ? field.replace('_', '-') + '-after-value'
          : null}
      >
      {after}
      </li>
    </ul>
  </dd>
</div>
