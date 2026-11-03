<script lang="ts">
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { TERMINOLOGY_FIELDS, type TerminologyField } from '#lib/utils/terminology-fields.js';
	import { m } from '#paraglide/messages.js';
	import type { PageData } from './$types';

	interface FieldSummary {
		field_path: string;
		label: string;
		count: number;
		visible_count: number;
		colors: string[];
	}

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const HEX = /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/;
	const FALLBACK = '#94a3b8';
	const PREVIEW_SIZE = 8;

	const labelOf = (field: FieldSummary) =>
		safeTranslate(TERMINOLOGY_FIELDS[field.field_path as TerminologyField] ?? field.label);

	let fields = $derived(
		[...((data.fields ?? []) as FieldSummary[])].sort((a, b) =>
			labelOf(a).localeCompare(labelOf(b))
		)
	);
</script>

<div class="bg-surface-50-950 shadow-sm flex flex-col">
	<header class="flex flex-col gap-1 px-6 pt-6 pb-5 border-b border-surface-200-800">
		<h1 class="text-2xl font-semibold tracking-tight text-surface-950-50">
			<i class="fa-solid fa-spell-check mr-2 text-surface-500"></i>{m.terminologies()}
		</h1>
		<p class="text-sm text-surface-600-400 max-w-2xl">{m.terminologyFieldsDescription()}</p>
	</header>

	<ul class="flex flex-col divide-y divide-surface-200-800" data-testid="terminology-fields">
		{#each fields as field (field.field_path)}
			<li>
				<a
					href={`/terminologies/${field.field_path}`}
					class="flex flex-wrap items-center gap-4 px-6 py-3.5 transition-colors hover:bg-surface-100-900"
					data-testid="terminology-field-row"
				>
					<div class="flex min-w-56 flex-1 flex-col">
						<span class="font-medium text-surface-950-50">{labelOf(field)}</span>
						<code class="text-xs text-surface-500">{field.field_path}</code>
					</div>

					<div class="flex items-center gap-1" aria-hidden="true">
						{#each field.colors.slice(0, PREVIEW_SIZE) as color, index (index)}
							<span
								class="size-3.5 rounded-full ring-1 ring-surface-300-700"
								style="background: {HEX.test(color) ? color : FALLBACK}"
							></span>
						{/each}
						{#if field.colors.length > PREVIEW_SIZE}
							<span class="ml-1 text-xs text-surface-500"
								>+{field.colors.length - PREVIEW_SIZE}</span
							>
						{/if}
					</div>

					<div class="flex min-w-36 flex-col items-end text-sm">
						<span class="tabular-nums text-surface-800-200"
							>{m.terminologyValuesCount({ count: field.count })}</span
						>
						{#if field.count > field.visible_count}
							<span class="text-xs tabular-nums text-surface-500"
								>{m.terminologyHiddenCount({ count: field.count - field.visible_count })}</span
							>
						{/if}
					</div>

					<i class="fa-solid fa-chevron-right text-xs text-surface-400"></i>
				</a>
			</li>
		{/each}
	</ul>
</div>
