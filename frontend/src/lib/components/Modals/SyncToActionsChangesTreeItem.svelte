<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';

	export interface SyncToActionsFieldChange {
		current: string;
		new: string;
	}

	export interface SyncToActionsTreeNode {
		key: string;
		label: string;
		children: SyncToActionsTreeNode[];
		changes: SyncToActionsFieldChange[];
		syncCount: number;
	}

	interface Props {
		node: SyncToActionsTreeNode;
	}

	let { node }: Props = $props();

	const hasChildren = $derived(node.children.length > 0);
	const hasChanges = $derived(node.changes.length > 0);
	const visibleChanges = $derived(node.changes.slice(0, 1));
</script>

<li class="text-sm">
	{#if hasChildren}
		<details open class="group">
			<summary
				class="flex cursor-pointer list-none items-center gap-2 rounded px-2 py-1.5 text-gray-800 hover:bg-gray-50 [&::-webkit-details-marker]:hidden"
			>
				<span class="w-3 text-xs text-gray-400">
					<span class="inline-block transition-transform group-open:rotate-90">›</span>
				</span>
				<span class="min-w-0 flex-1 break-words font-medium">{node.label}</span>
				{#if hasChanges}
					{#each visibleChanges as change}
						<span class="flex flex-wrap items-center gap-1.5 text-xs text-gray-700">
							<span class="rounded bg-gray-100 px-1.5 py-0.5">{safeTranslate(change.current)}</span>
							<span class="text-gray-400">-&gt;</span>
							<span class="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-800">
								{safeTranslate(change.new)}
							</span>
						</span>
					{/each}
				{/if}
				<span class="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-800">
					{node.syncCount}
				</span>
			</summary>

			<ul class="ml-6 space-y-1 border-l border-gray-200 pl-3">
				{#each node.children as child (child.key)}
					<svelte:self node={child} />
				{/each}
			</ul>
		</details>
	{:else}
		<div class="rounded px-2 py-1.5 text-gray-800">
			<div class="flex flex-wrap items-center gap-2">
				<span class="min-w-0 flex-1 break-words font-medium">{node.label}</span>
				{#if hasChanges}
					{#each visibleChanges as change}
						<span class="flex flex-wrap items-center gap-1.5 text-xs text-gray-700">
							<span class="rounded bg-gray-100 px-1.5 py-0.5">{safeTranslate(change.current)}</span>
							<span class="text-gray-400">-&gt;</span>
							<span class="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-800">
								{safeTranslate(change.new)}
							</span>
						</span>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</li>
