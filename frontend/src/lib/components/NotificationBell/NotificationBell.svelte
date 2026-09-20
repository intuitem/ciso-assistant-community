<script lang="ts">
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { onMount } from 'svelte';

	/**
	 * Unread badge for the app bar.
	 *
	 * The stack is WSGI + Huey with no websockets, so the count is polled rather than
	 * pushed: on an interval, on navigation, and when the tab regains focus. The last
	 * two are what make it feel live -- marking things read on /notifications and
	 * coming back should not show a stale number for another minute.
	 */
	const POLL_INTERVAL_MS = 60_000;
	// Past this the exact number stops being information and starts being noise; the
	// badge also has to stay a badge rather than grow into the toolbar.
	const MAX_DISPLAYED = 99;

	let count = $state(0);
	let failed = $state(false);

	const label = $derived(count > MAX_DISPLAYED ? `${MAX_DISPLAYED}+` : String(count));
	const title = $derived(count > 0 ? m.unreadNotifications({ count }) : m.noUnreadNotifications());

	async function refresh() {
		try {
			const res = await fetch('/fe-api/notifications/unread-count');
			if (!res.ok) throw new Error(String(res.status));
			const data = await res.json();
			count = Number(data?.count ?? 0);
			failed = false;
		} catch (error) {
			// A failed poll must never break the app bar; keep the last known count.
			failed = true;
			console.error('Could not refresh the unread notification count:', error);
		}
	}

	onMount(() => {
		// No initial refresh here: the $effect below already fires on mount.
		const interval = setInterval(refresh, POLL_INTERVAL_MS);
		const onFocus = () => {
			if (document.visibilityState === 'visible') refresh();
		};
		document.addEventListener('visibilitychange', onFocus);
		return () => {
			clearInterval(interval);
			document.removeEventListener('visibilitychange', onFocus);
		};
	});

	// Re-poll on navigation: the count changes as a side effect of using the inbox.
	$effect(() => {
		page.url.pathname;
		refresh();
	});
</script>

<a
	href="/notifications"
	class="relative flex items-center justify-center w-9 h-9 rounded-lg text-surface-600-400
	hover:bg-surface-200-800 hover:text-surface-900-100 transition-colors duration-150"
	aria-label={title}
	{title}
	data-testid="notification-bell"
>
	<i class="fa-regular fa-bell text-lg" class:text-surface-400-600={failed}></i>
	{#if count > 0}
		<span
			class="absolute -top-0.5 -right-0.5 min-w-4 h-4 px-1 flex items-center justify-center
			rounded-full bg-error-500 text-white text-[10px] font-semibold leading-none"
			data-testid="notification-bell-badge"
		>
			{label}
		</span>
	{/if}
</a>
