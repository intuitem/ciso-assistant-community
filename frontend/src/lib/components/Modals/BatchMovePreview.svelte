<script module lang="ts">
	type CascadeObject = { id: string; name: string };
	type CascadeGroup = { model: string; verbose_name?: string; objects: CascadeObject[] };

	/** Response of the `batch-cascade-info` endpoint: what the moved domains carry along. */
	export type BatchMovePreviewInfo = {
		deleted: {
			count: number;
			/** Objects in domains the user may not view: counted, never named. */
			hidden_count?: number;
			grouped_objects: CascadeGroup[];
		};
	};
</script>

<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import { SvelteSet } from 'svelte/reactivity';

	interface Props {
		preview: BatchMovePreviewInfo;
	}

	let { preview }: Props = $props();

	const carried = $derived(preview.deleted);
	const total = $derived(carried.count + (carried.hidden_count ?? 0));

	const expanded = new SvelteSet<string>();
	function toggle(model: string): void {
		if (expanded.has(model)) expanded.delete(model);
		else expanded.add(model);
	}
</script>

{#if total > 0}
	<div class="p-4 bg-blue-50 dark:bg-blue-500/15 border-l-2 border-blue-400">
		<div class="text-sm font-medium text-surface-950-50 mb-3">
			{m.batchMoveCarriedNotice({ count: total })}
		</div>
		<div class="max-h-64 overflow-y-auto space-y-1">
			{#each carried.grouped_objects as group (group.model)}
				<section class="border-t border-surface-200-800">
					<button
						type="button"
						class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-50-950 text-sm"
						aria-controls={`mov-${group.model}`}
						aria-expanded={expanded.has(group.model)}
						onclick={() => toggle(group.model)}
					>
						<span class="font-medium text-surface-950-50">{group.verbose_name ?? group.model}</span>
						<span class="text-xs text-surface-600-400">{group.objects.length}</span>
					</button>

					{#if expanded.has(group.model)}
						<ul id={`mov-${group.model}`} class="px-3 pb-2 text-sm space-y-0.5 bg-surface-50-950">
							{#each group.objects as o (o.id)}
								<li class="flex items-center justify-between py-1">
									<span class="truncate text-surface-700-300" title={o.name}>{o.name}</span>
								</li>
							{/each}
						</ul>
					{/if}
				</section>
			{/each}
			{#if carried.hidden_count}
				<p class="px-3 pt-2 text-xs text-surface-600-400" data-testid="cascade-hidden-objects">
					{m.cascadeHiddenObjects({ count: carried.hidden_count })}
				</p>
			{/if}
		</div>
	</div>
{/if}
