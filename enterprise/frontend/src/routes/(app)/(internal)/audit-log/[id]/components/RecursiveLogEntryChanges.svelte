<script lang="ts">
  import { safeTranslate } from '$lib/utils/i18n';
  import LogEntryChange from './LogEntryChange.svelte';
  import RecursiveLogEntryChanges from './RecursiveLogEntryChanges.svelte';

  type ProcessedValue = string | number | boolean | null | Record<string, any> | Array<any>;

  export let log: { changes: Record<string, any> };

  /**
   * Attempts to parse a value if it's a JSON string.
   * Returns the original value otherwise or if parsing fails.
   */
  const tryParseJsonIfNeeded = (item: any): ProcessedValue => {
    if (typeof item === 'string') {
      try {
        return JSON.parse(item);
      } catch (e) {
        // Parsing failed, return original string
        return item;
      }
    }
    // Not a string, return as is
    return item;
  };

  // Define the structure for a single processed change
  interface ProcessedChange {
    before: ProcessedValue;
    after: ProcessedValue;
  }

  const deepCompare = (val1: ProcessedValue, val2: ProcessedValue): boolean => {
     if (typeof val1 !== 'object' || val1 === null || typeof val2 !== 'object' || val2 === null) {
       return val1 === val2;
     }
     try {
        return JSON.stringify(val1) === JSON.stringify(val2);
     } catch (e) {
        // Handle potential stringify errors (e.g., circular references), unlikely here
        console.error("Error during deep comparison using JSON.stringify:", e);
        return false; // Assume not equal if stringify fails
     }
  };

  // Calculate the changes, filtering out non-changes
  const changes: Record<string, ProcessedChange> = Object.entries(log.changes || {}) // Handle case where log.changes might be undefined
    .reduce((acc, [key, value]) => {
      // Ensure the value is structured as expected
      if (Array.isArray(value) && value.length === 2) {
        const beforeValue = value[0];
        const afterValue = value[1];

        // Process both the 'before' and 'after' values first
        const processedBefore = tryParseJsonIfNeeded(beforeValue);
        const processedAfter = tryParseJsonIfNeeded(afterValue);

        if (deepCompare(processedBefore, processedAfter)) {
           // If values are identical after processing, skip this entry
           return acc;
        }

        acc[key] = {
          before: processedBefore,
          after: processedAfter
        };
      } else {
        console.warn(`Value for key "${key}" is not in the expected [before, after] format. Skipping.`, value);
      }

      return acc;
    }, {} as Record<string, ProcessedChange>); // Initialize with correct type

</script>

<dl class="px-4 py-1 text-sm flex flex-col space-y-4">
  {#each Object.entries(changes) as [field, change]}
    <div>
    {#if typeof change.before === 'object' && change.before !== null && typeof change.after === 'object' && change.after !== null && !Array.isArray(change.before) && !Array.isArray(change.after)}
      <dt
        class="font-medium text-gray-900"
        data-testid="{field.replace('_', '-')}-field-title"
      >
        {safeTranslate(field)}
      </dt>
      {@const allKeys = [...new Set([...Object.keys(change.before), ...Object.keys(change.after)])]}
      {#each allKeys as subKey}
         {@const subLog = { changes: { [subKey]: [change.before[subKey], change.after[subKey]] } }}
         <dd class="pl-4"> <RecursiveLogEntryChanges log={subLog} />
         </dd>
      {/each}
    {:else}
      <LogEntryChange
        field={field}
        before={change.before}
        after={change.after}
      />
    {/if}
    </div>
  {/each}
</dl>
