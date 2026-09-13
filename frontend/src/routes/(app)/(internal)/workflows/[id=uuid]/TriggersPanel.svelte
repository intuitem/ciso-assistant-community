<script lang="ts">
	import { Switch } from '@skeletonlabs/skeleton-svelte';
	import { m } from '$paraglide/messages';
	import { fetchHookSecret, publicHookUrl } from './hook-url';
	import { postOps } from './ops';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime';
	import { TRIGGER_ICONS } from './nodes/TriggerNode.svelte';

	interface Props {
		registrations: any[];
		workflowId: string;
		onRefresh: () => void;
	}

	let { registrations, workflowId, onRefresh }: Props = $props();

	const ops = (action: string, body: Record<string, unknown>) => postOps(workflowId, action, body);

	async function toggleEnabled(registration: any) {
		const res = await ops('toggle-trigger', {
			id: registration.id,
			enabled: !registration.enabled
		});
		if (res.ok) onRefresh();
	}

	async function rotateSecret(registration: any) {
		const res = await ops('rotate-trigger-secret', { id: registration.id });
		if (res.ok) {
			const body = await res.json().catch(() => ({}));
			if (typeof body.secret === 'string') hookSecrets[registration.id] = body.secret;
			onRefresh();
		}
	}

	// Secrets are change-gated server-side and fetched per trigger; viewers
	// get none and the URL column simply stays hidden for them.
	let hookSecrets = $state<Record<string, string>>({});
	$effect(() => {
		for (const registration of registrations) {
			if (registration.type !== 'webhook' || registration.id in hookSecrets) continue;
			fetchHookSecret(workflowId, registration.id).then((secret) => {
				if (secret) hookSecrets[registration.id] = secret;
			});
		}
	});

	function hookUrl(registration: any): string {
		const secret = hookSecrets[registration.id];
		return secret ? publicHookUrl(workflowId, registration.node_ref, secret) : '';
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
		skipped_coalesced: {
			class: 'preset-tonal-warning',
			label: () => m.triggerResultSkippedCoalesced()
		},
		error: { class: 'preset-tonal-error', label: () => m.triggerResultError() }
	};

	function formatWhen(iso: string | null): string {
		return formatDateOrDateTime(iso, getLocale()) ?? '—';
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
					<!-- Switch + state word: knob position is the state, so it can't be
					     misread as an action icon (play/pause was ambiguous both ways). -->
					<Switch
						name="trigger-enabled-{registration.id}"
						checked={registration.enabled}
						onCheckedChange={() => toggleEnabled(registration)}
						data-testid="toggle-trigger"
					>
						<Switch.Control class="scale-75 -mx-1">
							<Switch.Thumb />
						</Switch.Control>
						<Switch.HiddenInput />
						<span
							class="w-14 text-[10px] font-semibold uppercase tracking-wide {registration.enabled
								? 'text-success-600'
								: 'text-surface-500'}"
						>
							{registration.enabled ? m.triggerEnabled() : m.triggerDisabled()}
						</span>
					</Switch>
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
						{#if hookUrl(registration)}
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
						{/if}
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
