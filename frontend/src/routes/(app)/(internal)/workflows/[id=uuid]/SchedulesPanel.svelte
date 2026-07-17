<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		workflowId: string;
	}

	let { workflowId }: Props = $props();

	let schedules = $state<any[]>([]);
	let loading = $state(true);
	let error = $state('');
	let editingId = $state<string | null>(null);

	let form = $state({ name: '', cron_expression: '', timezone: 'UTC' });

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

	// Backend validation errors arrive as message keys (e.g. cronIntervalTooShort).
	function localizeError(data: any): string {
		const first = Object.values(data ?? {}).flat()[0];
		const key = typeof first === 'string' ? first : '';
		return (m as any)[key]?.() ?? (key || m.anErrorOccurred());
	}

	export async function refresh() {
		const res = await ops('list-schedules', { workflow: workflowId });
		if (res.ok) {
			const data = await res.json();
			schedules = data.results ?? data;
		}
		loading = false;
	}

	async function submit(event: Event) {
		event.preventDefault();
		error = '';
		const payload = { ...form, workflow: workflowId };
		const res = editingId
			? await ops('update-schedule', { id: editingId, patch: form })
			: await ops('create-schedule', payload);
		if (!res.ok) {
			error = localizeError(await res.json().catch(() => ({})));
			return;
		}
		form = { name: '', cron_expression: '', timezone: 'UTC' };
		editingId = null;
		await refresh();
	}

	function startEdit(schedule: any) {
		editingId = schedule.id;
		form = {
			name: schedule.name,
			cron_expression: schedule.cron_expression,
			timezone: schedule.timezone
		};
		error = '';
	}

	function cancelEdit() {
		editingId = null;
		form = { name: '', cron_expression: '', timezone: 'UTC' };
		error = '';
	}

	async function toggleEnabled(schedule: any) {
		const res = await ops('update-schedule', {
			id: schedule.id,
			patch: { enabled: !schedule.enabled }
		});
		if (res.ok) await refresh();
	}

	async function remove(id: string) {
		const res = await ops('delete-schedule', { id });
		if (res.ok) {
			if (editingId === id) cancelEdit();
			await refresh();
		}
	}

	$effect(() => {
		refresh();
	});

	const RESULT_BADGE: Record<string, { class: string; label: () => string }> = {
		triggered: { class: 'preset-tonal-success', label: () => m.scheduleResultTriggered() },
		skipped_overlap: {
			class: 'preset-tonal-warning',
			label: () => m.scheduleResultSkippedOverlap()
		},
		skipped_unpublished: {
			class: 'preset-tonal-warning',
			label: () => m.scheduleResultSkippedUnpublished()
		},
		error: { class: 'preset-tonal-error', label: () => m.scheduleResultError() }
	};

	function formatWhen(iso: string | null): string {
		if (!iso) return '—';
		return new Date(iso).toLocaleString();
	}
</script>

<div
	class="h-60 shrink-0 border-t border-surface-200-800 bg-surface-100-900 overflow-y-auto"
	data-testid="schedules-panel"
>
	<form class="flex items-end gap-2 px-4 pt-3 pb-2" onsubmit={submit}>
		<label class="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-surface-500">
			{m.name()}
			<input
				type="text"
				class="input text-xs w-36"
				bind:value={form.name}
				required
				data-testid="schedule-name"
			/>
		</label>
		<label class="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-surface-500">
			{m.cronExpression()}
			<input
				type="text"
				class="input text-xs w-36 font-mono"
				placeholder="0 3 * * *"
				bind:value={form.cron_expression}
				required
				data-testid="schedule-cron"
			/>
		</label>
		<label class="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-surface-500">
			{m.scheduleTimezone()}
			<input
				type="text"
				class="input text-xs w-36"
				placeholder="UTC"
				bind:value={form.timezone}
				data-testid="schedule-timezone"
			/>
		</label>
		<button type="submit" class="btn preset-filled-primary-500 text-xs" data-testid="add-schedule">
			{#if editingId}
				<i class="fa-solid fa-check mr-1"></i>{m.save()}
			{:else}
				<i class="fa-solid fa-plus mr-1"></i>{m.addSchedule()}
			{/if}
		</button>
		{#if editingId}
			<button type="button" class="btn preset-tonal text-xs" onclick={cancelEdit}>
				{m.cancel()}
			</button>
		{/if}
		{#if error}
			<span class="text-xs text-error-500 pb-2">{error}</span>
		{:else}
			<span class="text-[10px] text-surface-500 pb-2 truncate">
				{m.cronExpressionHint()}
			</span>
		{/if}
	</form>

	{#if loading}
		<p class="p-4 text-xs text-surface-500">
			<i class="fa-solid fa-spinner fa-spin mr-1"></i>
		</p>
	{:else if !schedules.length}
		<p class="p-4 text-xs text-surface-500 text-center">
			<i class="fa-solid fa-clock block text-lg mb-2 opacity-40"></i>
			{m.noSchedulesYet()}
		</p>
	{:else}
		<ul class="divide-y divide-surface-200-800">
			{#each schedules as schedule (schedule.id)}
				{@const badge = RESULT_BADGE[schedule.last_result]}
				<li class="flex items-center gap-3 px-4 py-2 text-xs">
					<button
						type="button"
						role="switch"
						aria-checked={schedule.enabled}
						title={m.enabled()}
						class="btn-icon w-6 h-6 text-[10px] {schedule.enabled
							? 'preset-filled-success-500'
							: 'preset-tonal'}"
						onclick={() => toggleEnabled(schedule)}
						data-testid="toggle-schedule"
					>
						<i class="fa-solid {schedule.enabled ? 'fa-play' : 'fa-pause'}"></i>
					</button>
					<span class="font-semibold text-surface-800-200 truncate">{schedule.name}</span>
					<span class="font-mono text-surface-600-400">{schedule.cron_expression}</span>
					<span class="text-surface-500">{schedule.timezone}</span>
					{#if schedule.enabled}
						<span class="text-surface-500" title={m.scheduleNextRun()}>
							<i class="fa-regular fa-clock mr-1"></i>{formatWhen(schedule.next_run_at)}
						</span>
					{/if}
					{#if badge}
						<span class="badge {badge.class} text-[9px]" title={formatWhen(schedule.last_run_at)}>
							{badge.label()}
						</span>
					{/if}
					<span class="ml-auto flex items-center gap-1 shrink-0">
						<button
							type="button"
							title={m.edit()}
							class="btn-icon preset-tonal w-6 h-6 text-[10px]"
							onclick={() => startEdit(schedule)}
							data-testid="edit-schedule"
						>
							<i class="fa-solid fa-pen"></i>
						</button>
						<button
							type="button"
							title={m.delete()}
							class="btn-icon preset-tonal w-6 h-6 text-[10px] hover:preset-filled-error-500"
							onclick={() => remove(schedule.id)}
							data-testid="delete-schedule"
						>
							<i class="fa-solid fa-trash"></i>
						</button>
					</span>
				</li>
			{/each}
		</ul>
	{/if}
</div>
