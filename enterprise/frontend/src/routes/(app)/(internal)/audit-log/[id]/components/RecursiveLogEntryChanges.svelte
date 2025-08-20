<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import LogEntryChange from './LogEntryChange.svelte';
	import RecursiveLogEntryChanges from './RecursiveLogEntryChanges.svelte';

	type ProcessedValue = string | number | boolean | null | Record<string, any> | Array<any>;

	interface Props {
    log: { action: string, changes: Record<string, any>};
	}

	let { log }: Props = $props();

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
			console.error('Error during deep comparison using JSON.stringify:', e);
			return false; // Assume not equal if stringify fails
		}
	};
	// Calculate the changes, filtering out non-changes
	const changes: Record<string, ProcessedChange> = Object.entries(log.changes || {}) // Handle case where log.changes might be undefined
		.reduce(
			(acc, [key, value]) => {
				// Ensure the value is structured as expected
				if (Array.isArray(value) && value.length === 2) {
					const beforeValue = value[0];
					const afterValue = value[1];

					// Process both the 'before' and 'after' values first
					let processedBefore = tryParseJsonIfNeeded(beforeValue);
					let processedAfter = tryParseJsonIfNeeded(afterValue);


					if (deepCompare(processedBefore, processedAfter)) {
						// If values are identical after processing, skip this entry
						return acc;
					}
          if (processedBefore === null || processedBefore === ""|| Array.isArray(processedBefore) && Object.keys(processedBefore).length === 0) {
             processedBefore = "None";
          }
          if (processedAfter === null || processedAfter === "" || Array.isArray(processedAfter) && Object.keys(processedAfter).length === 0) {
            processedAfter = "None";
          }

					acc[key] = {
						before: processedBefore,
						after: processedAfter
					};
				} else {
					console.warn(
						`Value for key "${key}" is not in the expected [before, after] format. Skipping.`,
						value
					);
				}

				return acc;
			},
			{} as Record<string, ProcessedChange>
		);
</script>

<dl class="px-4 text-sm flex flex-col">
	{#each Object.entries(changes) as [field, change]}
		<div class="w-full py-1">
			{#if typeof change.before === 'object' && change.before !== null && typeof change.after === 'object' && change.after !== null && !Array.isArray(change.before) && !Array.isArray(change.after)}
				{@const allKeys = [
					...new Set([...Object.keys(change.before), ...Object.keys(change.after)])
				]}
				<div class="ml-4">
					<dt class="font-medium text-gray-900" data-testid="{field.replace('_', '-')}-field-title">
						{safeTranslate(field)}
					</dt>
					<span class="flex flex-row h-full border-l border-gray-50 border-dashed">
						<div class="w-full">
							{#each allKeys as subKey}
								{@const subLog = {
									changes: { [subKey]: [change.before[subKey], change.after[subKey]] }
								}}
								<dd class="pl-4">
									<RecursiveLogEntryChanges log={subLog} />
								</dd>
							{/each}
						</div>
					</span>
				</div>
			{:else}
				<LogEntryChange action={log.action} {field} before={change.before} after={change.after} />
			{/if}
		</div>
	{/each}
</dl>
