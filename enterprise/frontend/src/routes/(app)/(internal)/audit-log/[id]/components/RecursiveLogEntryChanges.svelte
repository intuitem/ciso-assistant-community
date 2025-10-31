<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import LogEntryChange from './LogEntryChange.svelte';

	type ProcessedValue = string | number | boolean | null | Record<string, any> | Array<any>;

	// Define the structure for a single processed change
	interface ProcessedChange {
		before: ProcessedValue;
		after: ProcessedValue;
	}

	interface Props {
		log: { action: string; changes: Record<string, any> };
		level?: number; // Optional level for indentation or depth tracking
	}

	let { log, level = 0 }: Props = $props();

	/**
	 * Checks if a value is an object (but not an array or null).
	 */
	function isObjectLike(value: any): boolean {
		return typeof value === 'object' && value !== null && !Array.isArray(value);
	}

	/**
	 * Determines if a change involves nested objects.
	 * @param change The change object with before and after values.
	 * @returns True if either before or after is an object (and not null/array), false otherwise.
	 */
	function isNestedObjectChange(change: { before: any; after: any }): boolean {
		const isBeforeObjectLike = isObjectLike(change.before);
		const isAfterObjectLike = isObjectLike(change.after);
		return (
			(isBeforeObjectLike && isAfterObjectLike) ||
			(isBeforeObjectLike && change.after === 'None') ||
			(change.before === 'None' && isAfterObjectLike)
		);
	}

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

	/**
	 * Normalizes empty values to a consistent representation.
	 * @returns 'None' for null, undefined, empty strings, or empty objects; the original value otherwise.
	 */
	const normalizeEmptyValue = (value: any): ProcessedValue => {
		if (
			value == null ||
			value === '' ||
			(typeof value === 'object' && Object.keys(value).length === 0)
		) {
			return 'None';
		}
		return value;
	};

	/**
	 * Deeply compares two values for equality.
	 * Uses JSON.stringify for deep comparison, which works for most cases here.
	 * @returns True if values are deeply equal, false otherwise.
	 */
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

	/**
	 * Determines whether two values are effectively equal or ignorable.
	 * @returns True if values are deeply equal or ends with '.None' states (not to be confused with the string "None" which represents empty fields),
	 * false otherwise.
	 */
	function isSkippableChange(before: any, after: any): boolean {
		return (
			deepCompare(before, after) ||
			(typeof before === 'string' && before.endsWith('.None')) ||
			(typeof after === 'string' && after.endsWith('.None'))
		);
	}

	// Calculate the changes, filtering out non-changes
	const changes: Record<string, ProcessedChange> = Object.entries(log.changes || {}) // Handle case where log.changes might be undefined
		.reduce(
			(acc, [key, value]) => {
				key = key === 'id' ? 'UUID' : key;

				// Ensure the value is structured as expected
				if (Array.isArray(value) && value.length === 2) {
					const beforeValue = value[0];
					const afterValue = value[1];

					// Process both the 'before' and 'after' values first
					let processedBefore = tryParseJsonIfNeeded(beforeValue);
					let processedAfter = tryParseJsonIfNeeded(afterValue);

					if (isSkippableChange(processedBefore, processedAfter)) {
						return acc;
					}

					acc[key] = {
						// Normalize empty values happens after trying to parse JSON so it won't skip created entries that have an empty value
						// (on creation logs, the before will always be set to 'None'. If the after is 'None' too and you normalize first, it will skip)
						// (same for deletion logs, where the after will always be 'None')
						before: normalizeEmptyValue(processedBefore),
						after: normalizeEmptyValue(processedAfter)
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

<dl class="px-4 text-sm flex flex-col w-full" class:border-l-2={level > 0}>
	{#each Object.entries(changes) as [field, change]}
		<div class="w-full py-1">
			{#if isNestedObjectChange(change)}
				{@const allKeys = [
					...new Set([
						...Object.keys(isObjectLike(change.before) ? change.before : {}),
						...Object.keys(isObjectLike(change.after) ? change.after : {})
					])
				]}
				<div class="ml-4">
					<dt class="font-medium text-gray-900" data-testid="{field.replace('_', '-')}-field-title">
						{safeTranslate(field)}
					</dt>
					<span class="flex flex-row h-full border-l border-gray-50 border-dashed">
						<div class="w-full">
							{#each allKeys as subKey}
								{@const subLog = {
									changes: { [subKey]: [change.before[subKey], change.after[subKey]] },
									action: log.action
								}}
								<dd class="pl-4">
									<svelte:self log={subLog} level={level + 1} />
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
