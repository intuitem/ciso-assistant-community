<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { STATUS_BADGE } from './builder-constants';

	interface VersionRow {
		id: string;
		version_number: number;
		status: string;
		published_at?: string | null;
		run_count?: number;
		run_as?: string | null;
	}

	interface Props {
		versions: VersionRow[];
		activeVersionId: string;
		onSelect: (version: VersionRow) => void;
		onRestore?: (version: VersionRow) => void;
	}

	let { versions, activeVersionId, onSelect, onRestore }: Props = $props();

	const hasDraft = $derived(versions.some((v) => v.status === 'draft'));

	function formatWhen(value?: string | null) {
		if (!value) return '—';
		return formatDateOrDateTime(value, getLocale());
	}
</script>

<div
	class="h-60 shrink-0 border-t border-surface-200-800 bg-surface-100-900 overflow-y-auto"
	data-testid="versions-panel"
>
	<ul class="divide-y divide-surface-200-800">
		{#each versions as version (version.id)}
			{@const badge = STATUS_BADGE[version.status] ?? STATUS_BADGE.archived}
			<li>
				<div
					role="button"
					tabindex="0"
					class="w-full flex items-center gap-3 px-4 py-2 text-xs cursor-pointer text-left
					{version.id === activeVersionId ? 'bg-surface-50-950' : 'hover:bg-surface-50-950'}"
					onclick={() => onSelect(version)}
					onkeydown={(e) => {
						if ((e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget) {
							e.preventDefault();
							onSelect(version);
						}
					}}
					data-testid="version-row"
				>
					<span class="font-mono font-semibold text-surface-800-200 w-8">
						v{version.version_number}
					</span>
					<span class="badge {badge.class} text-[10px]">{badge.label()}</span>
					<span class="text-surface-500" title={m.publishedVersion()}>
						{formatWhen(version.published_at)}
					</span>
					{#if version.run_as}
						<span class="text-surface-500 shrink-0" title={m.runsAs({ user: version.run_as })}>
							<i class="fa-solid fa-user-shield mr-1 text-[9px] opacity-60"></i>{version.run_as}
						</span>
					{:else if version.status === 'published'}
						<span class="text-warning-600 shrink-0" title={m.republishRequired()}>
							<i class="fa-solid fa-user-slash mr-1 text-[9px]"></i>{m.runIdentityMissing()}
						</span>
					{/if}
					<span class="ml-auto text-surface-600-400 shrink-0">
						<i class="fa-solid fa-bolt-lightning mr-1 text-[9px]"></i>{version.run_count ?? 0}
						{m.workflowRuns().toLowerCase()}
					</span>
					{#if version.id === activeVersionId}
						<span class="badge preset-tonal-primary text-[9px] shrink-0">{m.viewing()}</span>
					{/if}
					{#if onRestore && version.status === 'archived'}
						<button
							type="button"
							class="btn-icon preset-tonal w-6 h-6 text-[10px] shrink-0"
							title={hasDraft ? m.restoreBlockedByDraft() : m.restoreAsDraft()}
							disabled={hasDraft}
							onclick={(e) => {
								e.stopPropagation();
								onRestore(version);
							}}
							data-testid="restore-version"
						>
							<i class="fa-solid fa-clock-rotate-left"></i>
						</button>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
</div>
