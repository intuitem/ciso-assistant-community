<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { FileEntry, BatchOutcome } from './types';

	interface Props {
		entries: FileEntry[];
		evidenceLinkPrefix?: string;
		onRemove?: (id: string) => void;
		disabled?: boolean;
	}

	let {
		entries = $bindable([]),
		evidenceLinkPrefix = '/evidences',
		onRemove,
		disabled = false
	}: Props = $props();

	function fmtSize(n: number): string {
		if (n < 1024) return `${n} B`;
		if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
		return `${(n / 1024 / 1024).toFixed(1)} MB`;
	}

	const outcomeBadge: Record<BatchOutcome, { label: string; cls: string; icon: string }> = $derived(
		{
			created: { label: m.created(), cls: 'bg-green-100 text-green-800', icon: 'fa-circle-plus' },
			revision_added: {
				label: m.revisionAdded(),
				cls: 'bg-blue-100 text-blue-800',
				icon: 'fa-code-branch'
			},
			replaced: { label: m.replaced(), cls: 'bg-violet-100 text-violet-800', icon: 'fa-rotate' },
			renamed: { label: m.renamed(), cls: 'bg-amber-100 text-amber-800', icon: 'fa-pen' },
			skipped: { label: m.skipped(), cls: 'bg-gray-100 text-gray-700', icon: 'fa-forward' },
			duplicate: { label: m.duplicate(), cls: 'bg-cyan-100 text-cyan-800', icon: 'fa-clone' },
			error: { label: m.error(), cls: 'bg-red-100 text-red-800', icon: 'fa-triangle-exclamation' }
		}
	);
</script>

{#if entries.length > 0}
	<div class="border rounded-lg overflow-hidden">
		<table class="w-full text-sm">
			<thead class="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
				<tr>
					<th class="px-3 py-2 font-medium">{m.pathOrName()}</th>
					<th class="px-3 py-2 font-medium">{m.size()}</th>
					<th class="px-3 py-2 font-medium">{m.status()}</th>
					<th class="px-3 py-2 font-medium">{m.detail()}</th>
					<th class="px-3 py-2"></th>
				</tr>
			</thead>
			<tbody>
				{#each entries as entry (entry.id)}
					<tr class="border-t">
						<td class="px-3 py-2">
							<div class="font-mono text-xs break-all">
								{entry.relPath || entry.name}
							</div>
							{#if entry.renamedTo && entry.renamedTo !== entry.name}
								<div class="text-xs text-amber-700">→ {entry.renamedTo}</div>
							{/if}
						</td>
						<td class="px-3 py-2 text-gray-600 whitespace-nowrap">{fmtSize(entry.size)}</td>
						<td class="px-3 py-2">
							{#if entry.status === 'pending'}
								<span class="text-gray-500"
									><i class="fa-regular fa-clock mr-1"></i>{m.pending()}</span
								>
							{:else if entry.status === 'uploading'}
								<span class="text-indigo-600"
									><i class="fa-solid fa-spinner fa-spin mr-1"></i>{m.uploading()}</span
								>
							{:else if entry.outcome}
								{@const b = outcomeBadge[entry.outcome]}
								<span class="px-2 py-0.5 rounded text-xs {b.cls}">
									<i class="fa-solid {b.icon} mr-1"></i>{b.label}
								</span>
							{/if}
						</td>
						<td class="px-3 py-2 text-xs text-gray-600">
							{#if entry.outcome === 'error' && entry.message}
								<span class="text-red-700">{entry.message}</span>
							{:else if entry.message}
								<span>{entry.message}</span>
							{:else if entry.evidenceId}
								<a
									href="{evidenceLinkPrefix}/{entry.evidenceId}"
									target="_blank"
									rel="noopener"
									class="text-indigo-600 hover:underline"
								>
									{m.evidence()}
									{#if entry.version}<span class="text-gray-500">v{entry.version}</span>{/if}
								</a>
							{/if}
						</td>
						<td class="px-3 py-2 text-right">
							{#if onRemove && entry.status !== 'uploading'}
								<button
									type="button"
									class="text-gray-400 hover:text-red-600"
									onclick={() => onRemove?.(entry.id)}
									{disabled}
									aria-label={m.remove()}
								>
									<i class="fa-solid fa-xmark"></i>
								</button>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
