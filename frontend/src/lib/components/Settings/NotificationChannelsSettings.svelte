<script lang="ts">
	import { getToastStore } from '$lib/components/Toast/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { Switch } from '@skeletonlabs/skeleton-svelte';
	import { onMount } from 'svelte';

	/**
	 * Which channels carry which notification type. The registry is the ceiling: a
	 * switch is disabled where its type does not support the channel, so an admin can
	 * narrow but never widen (docs §7). Grouped by category; 29 flat rows is unusable.
	 */
	type Channel = 'in_app' | 'email';
	type Row = {
		type: string;
		category: string;
		mode: string;
		supports_in_app: boolean;
		supports_email: boolean;
		in_app: boolean;
		email: boolean;
	};

	const CHANNELS: { key: Channel; label: () => string; icon: string }[] = [
		{ key: 'in_app', label: () => m.inApp(), icon: 'fa-solid fa-bell' },
		{ key: 'email', label: () => m.email(), icon: 'fa-solid fa-envelope' }
	];

	const toastStore = getToastStore();
	let rows: Row[] = $state([]);
	let loading = $state(true);
	let pending: Set<string> = $state(new Set());

	const groups = $derived(
		Object.entries(
			rows.reduce<Record<string, Row[]>>((acc, row) => {
				(acc[row.category] ??= []).push(row);
				return acc;
			}, {})
		)
	);

	function label(type: string): string {
		const pascal = type
			.split('_')
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join('');
		return safeTranslate(`template${pascal}Name`);
	}

	function description(type: string): string {
		const pascal = type
			.split('_')
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join('');
		const key = `template${pascal}Description`;
		const text = safeTranslate(key);
		// safeTranslate echoes the key back when there is no message for it.
		return text === key ? '' : text;
	}

	function enabledCount(group: Row[], channel: Channel): string {
		const supported = group.filter((row) => row[`supports_${channel}`]);
		return `${supported.filter((row) => row[channel]).length}/${supported.length}`;
	}

	async function load() {
		try {
			const res = await fetch('/fe-api/notification-channels');
			if (res.ok) rows = await res.json();
		} finally {
			loading = false;
		}
	}

	onMount(load);

	async function apply(type: string, channel: Channel, enabled: boolean) {
		const key = `${type}:${channel}`;
		pending = new Set(pending).add(key);
		try {
			const res = await fetch('/fe-api/notification-channels', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ type, channel, enabled })
			});
			if (!res.ok) throw new Error(String(res.status));
			// The endpoint answers with the whole matrix, so the view cannot drift.
			rows = await res.json();
		} catch (error) {
			toastStore.trigger({
				message: m.errorUpdatingObject({ object: m.notifications().toLowerCase() }),
				background: 'preset-filled-error-500'
			});
			console.error('Could not change notification channel:', error);
		} finally {
			const next = new Set(pending);
			next.delete(key);
			pending = next;
		}
	}

	async function applyToGroup(group: Row[], channel: Channel, enabled: boolean) {
		// Re-read each row from `rows` rather than the snapshot this loop started with:
		// every apply() replaces `rows` with the server's new matrix.
		for (const { type } of group) {
			const current = rows.find((row) => row.type === type);
			if (current?.[`supports_${channel}`] && current[channel] !== enabled) {
				await apply(type, channel, enabled);
			}
		}
	}
</script>

<div class="space-y-6 p-4">
	<p class="text-sm text-surface-600-400">{m.notificationChannelsDescription()}</p>

	{#if loading}
		<div class="text-sm text-surface-600-400">{m.loading()}...</div>
	{:else}
		{#each groups as [category, group] (category)}
			<div class="bg-surface-50-950 shadow-sm rounded-xl p-6 border border-surface-200-800">
				<div class="mb-4 flex items-start justify-between gap-4 flex-wrap">
					<h2 class="text-xl font-bold text-surface-950-50">{safeTranslate(category)}</h2>
					<div class="flex items-center gap-4 shrink-0">
						{#each CHANNELS as channel (channel.key)}
							{@const supported = group.some((row) => row[`supports_${channel.key}`])}
							{#if supported}
								<div class="flex items-center gap-2">
									<span class="text-xs text-surface-600-400 whitespace-nowrap">
										<i class="{channel.icon} mr-1"></i>{enabledCount(group, channel.key)}
									</span>
									<button
										type="button"
										class="btn btn-sm preset-tonal-primary"
										title={m.enableAll()}
										onclick={() => applyToGroup(group, channel.key, true)}
									>
										<i class="fa-solid fa-check"></i>
									</button>
									<button
										type="button"
										class="btn btn-sm preset-tonal"
										title={m.disableAll()}
										onclick={() => applyToGroup(group, channel.key, false)}
									>
										<i class="fa-solid fa-xmark"></i>
									</button>
								</div>
							{/if}
						{/each}
					</div>
				</div>

				<div class="divide-y divide-surface-200-800">
					{#each group as row (row.type)}
						<div class="flex items-center justify-between gap-4 py-3">
							<div class="min-w-0">
								<p class="font-medium text-surface-950-50 truncate">{label(row.type)}</p>
								{#if description(row.type)}
									<p class="text-sm text-surface-600-400">{description(row.type)}</p>
								{/if}
							</div>
							<div class="flex items-center gap-6 shrink-0">
								{#each CHANNELS as channel (channel.key)}
									{@const supports = row[`supports_${channel.key}`]}
									<div
										class="flex flex-col items-center gap-1"
										title={supports ? undefined : m.channelNotSupported()}
									>
										<span class="text-[10px] uppercase tracking-wide text-surface-600-400">
											{channel.label()}
										</span>
										<Switch
											name="{row.type}-{channel.key}"
											checked={row[channel.key]}
											disabled={!supports || pending.has(`${row.type}:${channel.key}`)}
											onCheckedChange={(e) => apply(row.type, channel.key, e.checked)}
											data-testid="channel-{row.type}-{channel.key}"
										>
											<Switch.Control>
												<Switch.Thumb />
											</Switch.Control>
											<Switch.HiddenInput />
										</Switch>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/each}
	{/if}
</div>
