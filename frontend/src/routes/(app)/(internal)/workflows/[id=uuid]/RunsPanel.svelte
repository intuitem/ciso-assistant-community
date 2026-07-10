<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		workflowId: string;
	}

	let { workflowId }: Props = $props();

	let runs = $state<any[]>([]);
	let expandedId = $state<string | null>(null);
	let logs = $state<Record<string, any[]>>({});
	let loading = $state(true);

	function opsUrl(action: string) {
		return `/workflows/${workflowId}/ops?action=${action}`;
	}

	export async function refresh() {
		const res = await fetch(opsUrl('list-instances'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ workflow: workflowId })
		});
		if (res.ok) {
			const data = await res.json();
			runs = data.results ?? data;
			if (expandedId) await loadLogs(expandedId);
		}
		loading = false;
	}

	async function loadLogs(instanceId: string) {
		const res = await fetch(opsUrl('instance-logs'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ instance: instanceId })
		});
		if (res.ok) logs = { ...logs, [instanceId]: await res.json() };
	}

	async function toggle(instanceId: string) {
		if (expandedId === instanceId) {
			expandedId = null;
			return;
		}
		expandedId = instanceId;
		await loadLogs(instanceId);
	}

	$effect(() => {
		refresh();
		const interval = setInterval(refresh, 4000);
		return () => clearInterval(interval);
	});

	const STATUS_STYLE: Record<string, { icon: string; class: string }> = {
		active: { icon: 'fa-circle-notch fa-spin', class: 'text-primary-500' },
		completed: { icon: 'fa-circle-check', class: 'text-success-500' },
		failed: { icon: 'fa-circle-xmark', class: 'text-error-500' },
		abandoned: { icon: 'fa-circle-minus', class: 'text-surface-500' }
	};

	function relativeTime(iso: string): string {
		const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
		if (seconds < 60) return `${seconds}s`;
		if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
		if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
		return `${Math.round(seconds / 86400)}d`;
	}
</script>

<div
	class="h-60 shrink-0 border-t border-surface-200-800 bg-surface-100-900 overflow-y-auto"
	data-testid="runs-panel"
>
	{#if loading}
		<p class="p-4 text-xs text-surface-500">
			<i class="fa-solid fa-spinner fa-spin mr-1"></i>
		</p>
	{:else if !runs.length}
		<p class="p-4 text-xs text-surface-500 text-center mt-6">
			<i class="fa-solid fa-bolt-lightning block text-lg mb-2 opacity-40"></i>
			{m.noRunsYet()}
		</p>
	{:else}
		<ul class="divide-y divide-surface-200-800">
			{#each runs as run (run.id)}
				{@const style = STATUS_STYLE[run.status] ?? STATUS_STYLE.abandoned}
				<li>
					<button
						type="button"
						class="w-full flex items-center gap-3 px-4 py-2 text-xs hover:bg-surface-50-950 cursor-pointer text-left"
						onclick={() => toggle(run.id)}
					>
						<i class="fa-solid {style.icon} {style.class}"></i>
						<span class="font-mono text-surface-500">{String(run.id).slice(0, 8)}</span>
						<span class="badge preset-tonal text-[9px] uppercase">{run.trigger}</span>
						<span class="text-surface-700-300">
							v{run.version?.version_number ?? '?'}
						</span>
						{#if run.active_nodes?.length}
							<span class="text-surface-600-400 truncate">
								{#each run.active_nodes as active}
									<span
										class="badge {active.status === 'error'
											? 'preset-tonal-error'
											: 'preset-tonal-warning'} text-[9px] mr-1"
									>
										{active.label}
									</span>
								{/each}
							</span>
						{/if}
						<span class="ml-auto text-surface-500 shrink-0">
							{relativeTime(run.created_at)}
						</span>
						<i
							class="fa-solid fa-chevron-{expandedId === run.id
								? 'up'
								: 'down'} text-surface-400-600"
						></i>
					</button>
					{#if expandedId === run.id}
						<div class="px-6 pb-3 bg-surface-50-950">
							<p class="text-[10px] font-semibold uppercase tracking-wide text-surface-500 py-1">
								{m.runDetails()}
							</p>
							<ol class="space-y-0.5">
								{#each logs[run.id] ?? [] as entry}
									<li class="flex items-start gap-2 text-[11px] font-mono">
										<span class="text-surface-400-600 shrink-0">
											{new Date(entry.created_at).toLocaleTimeString()}
										</span>
										<span
											class="shrink-0 {entry.event_type === 'error'
												? 'text-error-500'
												: entry.event_type === 'action_executed'
													? 'text-success-600'
													: 'text-surface-600-400'}"
										>
											{entry.event_type}
										</span>
										{#if entry.node}
											<span class="text-surface-800-200 shrink-0">
												{entry.node.label || entry.node.type}
											</span>
										{/if}
										{#if entry.message}
											<span class="text-surface-500 truncate">{entry.message}</span>
										{/if}
										{#if entry.data?.message}
											<span class="text-surface-700-300 italic truncate">
												“{entry.data.message}”
											</span>
										{/if}
										{#if entry.data?.created_object_name}
											<span class="badge preset-tonal-success text-[9px]">
												+ {entry.data.created_object_name}
											</span>
										{/if}
										{#if entry.data?.status !== undefined && entry.event_type === 'action_executed'}
											<span
												class="badge {entry.data.status >= 400
													? 'preset-tonal-error'
													: 'preset-tonal-success'} text-[9px]"
											>
												HTTP {entry.data.status}
											</span>
										{/if}
									</li>
								{/each}
							</ol>
						</div>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>
