<script lang="ts">
	import type { BatchSummary } from './types';

	interface Props {
		summary: BatchSummary | null;
	}

	let { summary }: Props = $props();

	const cells = [
		{ key: 'created', label: 'Created', cls: 'bg-green-50 text-green-800', icon: 'fa-circle-plus' },
		{
			key: 'revision_added',
			label: 'Revisions',
			cls: 'bg-blue-50 text-blue-800',
			icon: 'fa-code-branch'
		},
		{ key: 'replaced', label: 'Replaced', cls: 'bg-violet-50 text-violet-800', icon: 'fa-rotate' },
		{ key: 'renamed', label: 'Renamed', cls: 'bg-amber-50 text-amber-800', icon: 'fa-pen' },
		{ key: 'skipped', label: 'Skipped', cls: 'bg-gray-50 text-gray-700', icon: 'fa-forward' },
		{
			key: 'duplicate',
			label: 'Duplicates',
			cls: 'bg-cyan-50 text-cyan-800',
			icon: 'fa-clone'
		},
		{
			key: 'errors',
			label: 'Errors',
			cls: 'bg-red-50 text-red-800',
			icon: 'fa-triangle-exclamation'
		}
	] as const;
</script>

{#if summary}
	<div class="space-y-2">
		<div class="text-sm text-gray-600">
			Processed <strong>{summary.total}</strong> file(s).
		</div>
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
			{#each cells as cell}
				{@const count = summary[cell.key as keyof BatchSummary] ?? 0}
				<div class="p-3 rounded-lg {cell.cls}">
					<div class="text-xs uppercase tracking-wide">
						<i class="fa-solid {cell.icon} mr-1"></i>{cell.label}
					</div>
					<div class="text-2xl font-semibold">{count}</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
