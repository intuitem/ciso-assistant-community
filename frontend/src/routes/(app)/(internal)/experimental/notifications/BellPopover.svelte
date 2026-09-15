<script lang="ts">
	import { SEVERITY_META, type Notif } from './fixtures';
	import { relTime } from './time';

	interface Props {
		items: Notif[];
		onMarkAllRead: () => void;
		onOpen: (id: string) => void;
	}
	let { items, onMarkAllRead, onOpen }: Props = $props();

	let open = $state(false);
	const unread = $derived(items.filter((i) => !i.isRead));
	const newest = $derived(
		[...unread]
			.sort((a, b) => new Date(b.lastSeenAt).getTime() - new Date(a.lastSeenAt).getTime())
			.slice(0, 5)
	);
</script>

<div class="relative">
	<button
		onclick={() => (open = !open)}
		aria-label="Notifications"
		class="relative flex items-center gap-2 shrink-0 rounded-lg border border-surface-200-800 bg-surface-100-900/80 px-3 py-1.5
			text-xs text-surface-600-400 hover:bg-surface-200-800 hover:border-surface-300-700 transition-all duration-150 cursor-pointer"
	>
		<i class="fa-solid fa-bell text-surface-500"></i>
		{#if unread.length}
			<span
				class="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-white
					text-[10px] font-bold flex items-center justify-center"
			>
				{unread.length > 99 ? '99+' : unread.length}
			</span>
		{/if}
	</button>

	{#if open}
		<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
		<div class="fixed inset-0 z-40" onclick={() => (open = false)}></div>
		<div
			class="absolute right-0 top-10 z-50 w-96 rounded-lg border border-surface-200-800 bg-surface-50-950 shadow-xl overflow-hidden"
		>
			<div class="flex items-center justify-between px-3 py-2 border-b border-surface-200-800">
				<span class="text-sm font-semibold text-surface-800-200">
					Notifications
					{#if unread.length}<span class="text-surface-500 font-normal"
							>({unread.length} unread)</span
						>{/if}
				</span>
				<button
					class="text-xs text-primary-600 hover:underline cursor-pointer disabled:opacity-40 disabled:no-underline"
					disabled={!unread.length}
					onclick={onMarkAllRead}>Mark all read</button
				>
			</div>

			{#if newest.length === 0}
				<div class="px-3 py-8 text-center text-xs text-surface-500">
					<i class="fa-regular fa-bell-slash text-2xl mb-2 block opacity-40"></i>
					Nothing needs you right now.
				</div>
			{:else}
				<ul class="max-h-80 overflow-y-auto divide-y divide-surface-200-800">
					{#each newest as n (n.id)}
						<li>
							<button
								class="w-full text-left px-3 py-2.5 hover:bg-surface-100-900 cursor-pointer flex gap-2.5"
								onclick={() => {
									onOpen(n.id);
									open = false;
								}}
							>
								<span class="mt-1.5 size-2 shrink-0 rounded-full {SEVERITY_META[n.severity].dot}"
								></span>
								<span class="min-w-0 flex-1">
									<span class="block text-xs font-semibold text-surface-900-100 truncate"
										>{n.title}</span
									>
									<span class="block text-[11px] text-surface-500 mt-0.5">
										{relTime(n.lastSeenAt)}
										{#if n.seenCount > 1}
											· reminded {n.seenCount}×
										{/if}
									</span>
								</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}

			<a
				href="/experimental/notifications"
				class="block px-3 py-2 text-center text-xs text-primary-600 hover:bg-surface-100-900 border-t border-surface-200-800"
				onclick={() => (open = false)}>See all notifications</a
			>
		</div>
	{/if}
</div>
