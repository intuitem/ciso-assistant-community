<script lang="ts">
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';

	// The subject's own records a page shows, read-only (backend core.quick_form_facts):
	// live while the response is a draft, as they stood at submission after.
	interface Fact {
		label: string;
		columns: string[];
		rows: (string | boolean | null)[][];
	}
	interface Props {
		facts: Record<string, Fact>;
		keys: string[];
		frozen: boolean;
		/** Where the record is edited; none when the viewer cannot open it. */
		href?: string | null;
	}

	let { facts, keys, frozen, href = null }: Props = $props();

	const OPEN_UP_TO = 5;
	const shown = $derived(keys.filter((key) => facts[key]));
	const cell = (value: string | boolean | null) =>
		value === true ? m.yes() : value === false ? m.no() : value ? safeTranslate(value) : '—';
</script>

{#if shown.length}
	<div
		class="rounded-base border border-surface-200-800 bg-surface-100-900 p-3 space-y-3"
		data-testid="subject-facts"
	>
		<p class="flex flex-wrap items-center gap-2 text-xs text-surface-600-400">
			<i class="fa-solid fa-lock"></i>
			{frozen ? m.subjectFactsFrozen() : m.subjectFactsLive()}
			{#if href && !frozen}
				<a class="anchor" {href}>{m.subjectFactsEdit()}</a>
			{/if}
		</p>
		{#each shown as key (key)}
			{@const fact = facts[key]}
			<!-- Open when short: a long record should not bury the questions. -->
			<details open={fact.rows.length <= OPEN_UP_TO}>
				<summary class="cursor-pointer text-sm font-semibold">
					{safeTranslate(fact.label)}
					<span class="font-normal text-surface-500">({fact.rows.length})</span>
				</summary>
				{#if fact.rows.length}
					<div class="overflow-x-auto">
						<table class="table text-xs">
							<thead>
								<tr>
									{#each fact.columns as column (column)}<th>{safeTranslate(column)}</th>{/each}
								</tr>
							</thead>
							<tbody>
								{#each fact.rows as row, i (i)}
									<tr>
										{#each row as value, ci (ci)}<td>{cell(value)}</td>{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<p class="text-xs text-surface-500">{m.subjectFactsNone()}</p>
				{/if}
			</details>
		{/each}
	</div>
{/if}
