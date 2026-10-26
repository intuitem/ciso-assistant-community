<script module lang="ts">
	type CascadeObject = { id: string; name: string };
	type CascadeGroup = { model: string; verbose_name?: string; objects: CascadeObject[] };
	type CascadeBucket = {
		count: number;
		/** Objects in domains the user may not view: counted, never named. */
		hidden_count?: number;
		grouped_objects: CascadeGroup[];
		related_objects?: CascadeObject[];
		message?: string;
		level?: string;
	};

	/** Response of the `cascade-info` and `batch-cascade-info` endpoints. */
	export type CascadeInfo = {
		deleted: CascadeBucket;
		affected: CascadeBucket;
		blocked?: CascadeBucket;
	};

	function total(bucket: CascadeBucket | undefined): number {
		return (bucket?.count ?? 0) + (bucket?.hidden_count ?? 0);
	}

	/** Whether a PROTECT/RESTRICT reference makes the delete fail server-side,
	 * including one the user may not view. */
	export function isCascadeBlocked(cascadeInfo: CascadeInfo | null): boolean {
		return total(cascadeInfo?.blocked) > 0;
	}
</script>

<script lang="ts">
	import { m } from '$paraglide/messages';
	import { SvelteSet } from 'svelte/reactivity';

	type BucketName = 'deleted' | 'affected' | 'blocked';

	interface Props {
		cascadeInfo: CascadeInfo;
		/** `move` lists only what the subjects carry along: nothing is deleted, blocked
		 * or unlinked by a move. */
		mode?: 'delete' | 'move';
	}

	let { cascadeInfo, mode = 'delete' }: Props = $props();

	const isBlocked = $derived(mode === 'delete' && isCascadeBlocked(cascadeInfo));

	// Buckets share group keys, so the bucket name is part of the key.
	const expanded = new SvelteSet<string>();
	function keyFor(bucket: BucketName, groupKey: string): string {
		return `${bucket}:${groupKey}`;
	}
	function toggle(bucket: BucketName, groupKey: string): void {
		const k = keyFor(bucket, groupKey);
		if (expanded.has(k)) expanded.delete(k);
		else expanded.add(k);
	}
</script>

{#snippet groups(bucket: BucketName, idPrefix: string, data: CascadeBucket)}
	<div class="max-h-64 overflow-y-auto space-y-1">
		{#each data.grouped_objects as group (group.model)}
			<section class="border-t border-surface-200-800">
				<button
					type="button"
					class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-50-950 text-sm"
					aria-controls={`${idPrefix}-${group.model}`}
					aria-expanded={expanded.has(keyFor(bucket, group.model))}
					onclick={() => toggle(bucket, group.model)}
				>
					<span class="font-medium text-surface-950-50">{group.verbose_name ?? group.model}</span>
					<span class="text-xs text-surface-600-400">
						{group.objects.length}
					</span>
				</button>

				{#if expanded.has(keyFor(bucket, group.model))}
					<ul
						id={`${idPrefix}-${group.model}`}
						class="px-3 pb-2 text-sm space-y-0.5 bg-surface-50-950"
					>
						{#each group.objects as o (o.id)}
							<li class="flex items-center justify-between py-1">
								<span class="truncate text-surface-700-300" title={o.name}>{o.name}</span>
							</li>
						{/each}
					</ul>
				{/if}
			</section>
		{/each}
		{#if data.hidden_count}
			<p class="px-3 pt-2 text-xs text-surface-600-400" data-testid="cascade-hidden-objects">
				{m.cascadeHiddenObjects({ count: data.hidden_count })}
			</p>
		{/if}
	</div>
{/snippet}

{#if isBlocked && cascadeInfo.blocked}
	<div class="p-4 bg-error-50 dark:bg-error-500/15 border-l-2 border-error-500">
		<div class="text-sm font-medium text-surface-950-50 mb-3">
			{m.cascadeBlockedWarning({ count: total(cascadeInfo.blocked) })}
		</div>
		{@render groups('blocked', 'blk', cascadeInfo.blocked)}
	</div>
{/if}

{#if mode === 'move' && total(cascadeInfo.deleted) > 0}
	<div class="p-4 bg-blue-50 dark:bg-blue-500/15 border-l-2 border-blue-400">
		<div class="text-sm font-medium text-surface-950-50 mb-3">
			{m.batchMoveCarriedNotice({ count: total(cascadeInfo.deleted) })}
		</div>
		{@render groups('deleted', 'mov', cascadeInfo.deleted)}
	</div>
{/if}

{#if mode === 'delete' && !isBlocked && total(cascadeInfo.deleted) > 0}
	<div class="p-4 bg-orange-50 dark:bg-orange-500/15 border-l-2 border-orange-400">
		<div class="text-sm font-medium text-surface-950-50 mb-3">
			{m.cascadeDeleteWarning({ count: total(cascadeInfo.deleted) })}
		</div>
		{@render groups('deleted', 'del', cascadeInfo.deleted)}
	</div>
{/if}

{#if mode === 'delete' && !isBlocked && total(cascadeInfo.affected) > 0}
	<div class="p-4 bg-blue-50 dark:bg-blue-500/15 border-l-2 border-blue-400">
		<div class="text-sm font-medium text-surface-950-50 mb-1">
			{m.cascadeAffectedNotice({ count: total(cascadeInfo.affected) })}
		</div>
		<p class="text-xs text-surface-600-400 mb-3">
			{m.cascadeAffectedHint()}
		</p>
		{@render groups('affected', 'aff', cascadeInfo.affected)}
	</div>
{/if}
