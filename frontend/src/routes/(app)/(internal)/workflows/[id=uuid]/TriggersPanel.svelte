<script lang="ts">
	import { m } from '$paraglide/messages';
	import { TRIGGER_ICONS } from './nodes/TriggerNode.svelte';

	interface Props {
		registrations: any[];
		workflowId: string;
		onRefresh: () => void;
	}

	let { registrations, workflowId, onRefresh }: Props = $props();

	function opsUrl(action: string) {
		return `/workflows/${workflowId}/ops?action=${action}`;
	}

	async function ops(action: string, body: Record<string, unknown>) {
		return fetch(opsUrl(action), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
	}

	async function toggleEnabled(registration: any) {
		const res = await ops('toggle-trigger', {
			id: registration.id,
			enabled: !registration.enabled
		});
		if (res.ok) onRefresh();
	}

	async function rotateSecret(registration: any) {
		const res = await ops('rotate-trigger-secret', { id: registration.id });
		if (res.ok) onRefresh();
	}

	function hookUrl(registration: any): string {
		return `${location.origin}/api/workflows/hooks/${workflowId}/${registration.node_ref}/${registration.secret}/`;
	}

	let copiedId = $state<string | null>(null);
	async function copyHookUrl(registration: any) {
		await navigator.clipboard.writeText(hookUrl(registration));
		copiedId = registration.id;
		setTimeout(() => (copiedId = null), 1500);
	}

	const RESULT_BADGE: Record<string, { class: string; label: () => string }> = {
		triggered: { class: 'preset-tonal-success', label: () => m.triggerResultTriggered() },
		skipped_overlap: {
			class: 'preset-tonal-warning',
			label: () => m.triggerResultSkippedOverlap()
		},
		skipped_unpublished: {
			class: 'preset-tonal-warning',
			label: () => m.triggerResultSkippedUnpublished()
		},
		skipped_depth: {
			class: 'preset-tonal-warning',
			label: () => m.triggerResultSkippedDepth()
		},
		error: { class: 'preset-tonal-error', label: () => m.triggerResultError() }
	};

	function formatWhen(iso: string | null): string {
		if (!iso) return '—';
		return new Date(iso).toLocaleString();
	}

	function relativeTime(iso: string | null): string {
		if (!iso) return '—';
		const diff = new Date(iso).getTime() - Date.now();
		const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
		const units: [Intl.RelativeTimeFormatUnit, number][] = [
			['day', 86400000],
			['hour', 3600000],
			['minute', 60000]
		];
		for (const [unit, ms] of units) {
			if (Math.abs(diff) >= ms) return rtf.format(Math.round(diff / ms), unit);
		}
		return rtf.format(0, 'minute');
	}

	function truncate(text: string, max: number): string {
		return text.length > max ? `${text.slice(0, max)}…` : text;
	}
</script>

<div
	class="h-60 shrink-0 border-t border-surface-200-800 bg-surface-100-900 overflow-y-auto"
	data-testid="triggers-panel"
>
	{#if !registrations.length}
		<p class="p-4 text-xs text-surface-500 text-center mt-6">
			<i class="fa-solid fa-bolt block text-lg mb-2 opacity-40"></i>
			{m.noTriggersYet()}
		</p>
	{:else}
		<p class="px-4 pt-2 text-[10px] text-surface-500">
			{m.triggersAppearOnPublish()}
		</p>
		<ul class="divide-y divide-surface-200-800">
			{#each registrations as registration (registration.id)}
				{@const badge = RESULT_BADGE[registration.last_result]}
				{@const config = registration.config ?? {}}
				<li class="flex items-center gap-3 px-4 py-2 text-xs">
					<button
						type="button"
						role="switch"
						aria-checked={registration.enabled}
						title={registration.enabled ? m.triggerArmed() : m.triggerDisarmed()}
						class="btn-icon w-6 h-6 text-[10px] {registration.enabled
							? 'preset-filled-success-500'
							: 'preset-tonal'}"
						onclick={() => toggleEnabled(registration)}
						data-testid="toggle-trigger"
					>
						<i class="fa-solid {registration.enabled ? 'fa-play' : 'fa-pause'}"></i>
					</button>
					<i
						class="fa-solid {TRIGGER_ICONS[registration.type] ?? 'fa-bolt'} text-surface-500 w-4
						text-center shrink-0"
						title={registration.type}
					></i>
					<span class="font-mono text-surface-800-200 truncate">{registration.node_ref}</span>

					{#if registration.type === 'schedule'}
						<span class="font-mono text-surface-600-400">{config.cron_expression ?? ''}</span>
						{#if registration.enabled}
							<span class="text-surface-500" title={m.scheduleNextRun()}>
								<i class="fa-regular fa-clock mr-1"></i>{formatWhen(registration.next_run_at)}
							</span>
						{/if}
						<span class="text-surface-500" title={m.scheduleLastRun()}>
							{relativeTime(registration.last_run_at)}
						</span>
					{:else if registration.type === 'internal_event'}
						<span class="badge preset-tonal font-mono text-[9px]">{registration.event_key}</span>
						<span
							class="text-surface-500"
							title="{m.triggerLastFired()}: {formatWhen(registration.last_triggered_at)}"
						>
							<i class="fa-regular fa-clock mr-1"></i>{relativeTime(registration.last_triggered_at)}
						</span>
						<span class="badge preset-tonal text-[9px]">×{registration.trigger_count ?? 0}</span>
					{:else if registration.type === 'webhook'}
						<span class="font-mono text-surface-500 truncate" title={hookUrl(registration)}>
							{truncate(hookUrl(registration), 48)}
						</span>
						<button
							type="button"
							aria-label="Copy webhook URL"
							class="btn-icon preset-tonal w-6 h-6 text-[10px] shrink-0"
							onclick={() => copyHookUrl(registration)}
						>
							<i
								class="fa-solid {copiedId === registration.id
									? 'fa-check text-success-500'
									: 'fa-copy'}"
							></i>
						</button>
						<button
							type="button"
							title={m.rotateSecret()}
							class="btn-icon preset-tonal w-6 h-6 text-[10px] shrink-0"
							onclick={() => rotateSecret(registration)}
							data-testid="rotate-trigger-secret-row"
						>
							<i class="fa-solid fa-rotate"></i>
						</button>
					{/if}

					{#if badge}
						<span
							class="badge {badge.class} text-[9px] ml-auto shrink-0"
							title={formatWhen(registration.last_triggered_at ?? registration.last_run_at)}
						>
							{badge.label()}
						</span>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>
