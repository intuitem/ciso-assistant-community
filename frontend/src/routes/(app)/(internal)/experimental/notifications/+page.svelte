<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import BellPopover from './BellPopover.svelte';
	import NotificationRow from './NotificationRow.svelte';
	import {
		CATEGORY_META,
		EVENT_TYPES,
		NOTIFICATIONS,
		categoryOf,
		conditionKeyOf,
		isConditionBacked,
		type Category,
		type Notif
	} from './fixtures';
	import { NOW, relTime } from './time';

	$pageTitle = 'Notification centre (mock)';

	let items = $state<Notif[]>(NOTIFICATIONS.map((n) => ({ ...n })));
	/**
	 * objectIds whose condition is currently false. Seeded from the already-auto-cleared
	 * rows: a row the sweep cleared means its object got fixed, so a fresh sweep must not
	 * resurrect it.
	 */
	const initialFixed = () =>
		new Set(NOTIFICATIONS.filter((n) => n.autoClearedAt).map((n) => n.objectId));
	let fixed = $state<Set<string>>(initialFixed());
	let selected = $state<Set<string>>(new Set());
	let view = $state<'unread' | 'all' | 'cleared'>('unread');
	let category = $state<Category | 'all'>('all');
	let eventType = $state<string | 'all'>('all');
	let search = $state('');
	let sweepLog = $state<string[]>([]);
	let toast = $state('');

	const unreadCount = $derived(items.filter((i) => !i.isRead).length);
	const clearedCount = $derived(items.filter((i) => i.autoClearedAt).length);

	/** Event types offered in the dropdown, narrowed by the chosen category. */
	const typeOptions = $derived(
		Object.entries(EVENT_TYPES)
			.filter(([, meta]) => category === 'all' || meta.category === category)
			.sort((a, b) => a[1].label.localeCompare(b[1].label))
	);

	$effect(() => {
		// A category change can orphan the selected type; drop it rather than showing nothing.
		if (eventType !== 'all' && category !== 'all' && EVENT_TYPES[eventType].category !== category) {
			eventType = 'all';
		}
	});

	const visible = $derived(
		items
			.filter((i) =>
				view === 'unread' ? !i.isRead : view === 'cleared' ? Boolean(i.autoClearedAt) : true
			)
			.filter((i) => (category === 'all' ? true : categoryOf(i) === category))
			.filter((i) => (eventType === 'all' ? true : i.type === eventType))
			.filter((i) =>
				search.trim()
					? (i.title + i.body).toLowerCase().includes(search.trim().toLowerCase())
					: true
			)
			.sort((a, b) => new Date(b.lastSeenAt).getTime() - new Date(a.lastSeenAt).getTime())
	);

	const allVisibleSelected = $derived(
		visible.length > 0 && visible.every((i) => selected.has(i.id))
	);

	function toggleIn(set: Set<string>, id: string) {
		const next = new Set(set);
		next.has(id) ? next.delete(id) : next.add(id);
		return next;
	}

	function setRead(ids: string[], isRead: boolean) {
		items = items.map((i) => (ids.includes(i.id) ? { ...i, isRead } : i));
		selected = new Set();
	}

	function remove(ids: string[]) {
		items = items.filter((i) => !ids.includes(i.id));
		selected = new Set();
	}

	/** Opening a notification always does both: marks it read and goes to the destination. */
	function openNotification(n: Notif) {
		setRead([n.id], true);
		toast = `Would navigate to ${n.link}`;
		setTimeout(() => (toast = ''), 2500);
	}

	/**
	 * The whole write path in one button. Three rules, matching §4 of the shaping doc:
	 *   still true  → upsert (bump seenCount), never touching isRead
	 *   gone        → mark read, stamp autoClearedAt, release the dedupe key
	 *   true again  → the key is free, so a fresh unread row appears next to the old one
	 */
	function runSweep() {
		const now = new Date(NOW).toISOString();
		const log: string[] = [];
		const next: Notif[] = [];
		const activeKeys = new Set(items.map((i) => i.dedupeKey).filter(Boolean) as string[]);

		for (const i of items) {
			if (!isConditionBacked(i)) {
				next.push(i);
				continue;
			}
			const stillTrue = !fixed.has(i.objectId);

			if (!stillTrue) {
				if (i.dedupeKey) {
					next.push({ ...i, isRead: true, autoClearedAt: now, dedupeKey: null });
					log.push(`✓ ${i.title} — condition gone, marked read, dedupe key released`);
				} else {
					next.push(i);
				}
				continue;
			}

			if (!i.dedupeKey) {
				// Auto-cleared earlier and now true again. The unique constraint is what stops
				// this firing every night: only one row may hold the key at a time.
				next.push(i);
				const key = conditionKeyOf(i);
				if (!activeKeys.has(key)) {
					activeKeys.add(key);
					next.push({
						...i,
						id: `${i.id}-r${items.length}`,
						dedupeKey: key,
						isRead: false,
						autoClearedAt: null,
						seenCount: 1,
						createdAt: now,
						lastSeenAt: now
					});
					log.push(`↻ ${i.title} — true again, key was free, fired as a new unread row`);
				}
				continue;
			}

			const bumped = { ...i, seenCount: i.seenCount + 1, lastSeenAt: now };
			next.push(bumped);
			log.push(
				i.isRead
					? `· ${i.title} — still true but read, suppressed (no reopen)`
					: `· ${i.title} — still true, reminder count now ${bumped.seenCount}`
			);
		}
		items = next;
		sweepLog = log;
	}

	function reset() {
		items = NOTIFICATIONS.map((n) => ({ ...n }));
		fixed = initialFixed();
		selected = new Set();
		sweepLog = [];
	}
</script>

<div class="flex flex-col gap-4 p-4">
	<div class="card bg-surface-50-950 shadow-sm p-3 flex flex-wrap items-center gap-3">
		<h4 class="font-bold text-surface-800-200">
			<i class="fa-solid fa-bell mr-2"></i>Notification centre
		</h4>
		<span
			class="text-xs text-surface-500 px-2 py-0.5 rounded bg-surface-100-900 border border-surface-200-800"
			>mock data · no backend</span
		>
		<span class="text-xs text-surface-500">
			Two states only — <strong>unread</strong> and <strong>read</strong>. Read is the
			acknowledgement <em>and</em> the thing that stops the reminder.
		</span>
	</div>

	<!-- Surface 1: the AppBar bell, reproduced here since this page can't inject into the real one -->
	<div class="card bg-surface-50-950 shadow-sm p-3">
		<div class="flex items-center justify-between gap-3">
			<span class="text-xs text-surface-500">
				<i class="fa-solid fa-arrow-right mr-1"></i>
				Surface 1 — the bell, as it would sit in the app bar next to the theme toggle:
			</span>
			<BellPopover
				{items}
				onMarkAllRead={() =>
					setRead(
						items.filter((i) => !i.isRead).map((i) => i.id),
						true
					)}
				onOpen={(id) => setRead([id], true)}
			/>
		</div>
	</div>

	<!-- The write path, made pressable -->
	<div class="card bg-surface-50-950 shadow-sm p-3 flex flex-col gap-2">
		<div class="flex flex-wrap items-center gap-3">
			<button class="btn btn-sm preset-filled-primary-500" onclick={runSweep}>
				<i class="fa-solid fa-play mr-1.5"></i>Run tonight's 06:00 sweep
			</button>
			<button class="btn btn-sm preset-tonal" onclick={reset}>
				<i class="fa-solid fa-rotate-left mr-1.5"></i>Reset
			</button>
			<span class="text-xs text-surface-500">
				Use the <i class="fa-solid fa-wrench"></i> on a reminder row to pretend the underlying object
				got fixed, then run the sweep. Un-fix it and sweep again to watch the dedupe key re-arm.
			</span>
		</div>
		{#if sweepLog.length}
			<ul
				class="text-[11px] font-mono text-surface-600-400 bg-surface-100-900 rounded p-2 max-h-40 overflow-y-auto"
			>
				{#each sweepLog as line}
					<li class="truncate">{line}</li>
				{/each}
			</ul>
		{/if}
	</div>

	<!-- Surface 2: the inbox -->
	<div class="card bg-surface-50-950 shadow-sm overflow-hidden">
		<div class="flex flex-wrap items-center gap-2 p-3 border-b border-surface-200-800">
			<div class="flex rounded-lg border border-surface-200-800 overflow-hidden">
				{#each [['unread', `Unread (${unreadCount})`], ['all', `All (${items.length})`], ['cleared', `No longer applies (${clearedCount})`]] as [key, label]}
					<button
						class="px-3 py-1 text-xs cursor-pointer border-r border-surface-200-800 last:border-r-0 {view ===
						key
							? 'bg-primary-500 text-white'
							: 'bg-surface-50-950 text-surface-600-400 hover:bg-surface-100-900'}"
						onclick={() => (view = key as typeof view)}>{label}</button
					>
				{/each}
			</div>

			<select class="select select-sm text-xs w-auto" bind:value={category}>
				<option value="all">All categories</option>
				{#each Object.entries(CATEGORY_META) as [key, meta]}
					<option value={key}>{meta.label}</option>
				{/each}
			</select>

			<select class="select select-sm text-xs w-auto" bind:value={eventType}>
				<option value="all">All event types</option>
				{#each typeOptions as [key, meta]}
					<option value={key}>{meta.label}</option>
				{/each}
			</select>

			<input
				class="input input-sm text-xs w-56"
				type="search"
				placeholder="Search notifications…"
				bind:value={search}
			/>

			{#if toast}
				<span
					class="ml-auto text-xs px-2 py-1 rounded bg-primary-100 dark:bg-primary-950 text-primary-700 dark:text-primary-300"
				>
					<i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>{toast}
				</span>
			{:else}
				<span class="ml-auto text-xs text-surface-500">{visible.length} shown</span>
			{/if}
		</div>

		{#if selected.size}
			<div
				class="flex flex-wrap items-center gap-2 px-3 py-2 bg-primary-50 dark:bg-primary-950 border-b border-primary-200 dark:border-primary-800"
			>
				<span class="text-xs font-semibold text-primary-800 dark:text-primary-200">
					{selected.size} selected
				</span>
				<button
					class="btn btn-sm preset-tonal-primary text-xs"
					onclick={() => setRead([...selected], true)}
				>
					<i class="fa-solid fa-envelope-open mr-1.5"></i>Mark as read
				</button>
				<button
					class="btn btn-sm preset-tonal-primary text-xs"
					onclick={() => setRead([...selected], false)}
				>
					<i class="fa-solid fa-envelope mr-1.5"></i>Mark as unread
				</button>
				<button class="btn btn-sm preset-tonal-error text-xs" onclick={() => remove([...selected])}>
					<i class="fa-solid fa-trash mr-1.5"></i>Delete
				</button>
				<button
					class="text-xs text-surface-500 hover:underline ml-1 cursor-pointer"
					onclick={() => (selected = new Set())}
				>
					Clear selection
				</button>
			</div>
		{/if}

		{#if visible.length === 0}
			<div class="px-3 py-16 text-center text-sm text-surface-500">
				<i class="fa-regular fa-bell-slash text-3xl mb-3 block opacity-40"></i>
				Nothing matches these filters. Try <em>All</em>, or reset the mock.
			</div>
		{:else}
			<table class="w-full text-xs">
				<thead class="bg-surface-50-950 text-surface-700-300">
					<tr class="border-b border-surface-200-800">
						<th class="w-10 p-3">
							<input
								type="checkbox"
								class="checkbox"
								checked={allVisibleSelected}
								onchange={() =>
									(selected = allVisibleSelected ? new Set() : new Set(visible.map((i) => i.id)))}
								aria-label="Select all"
							/>
						</th>
						<th class="text-left font-semibold p-3">Notification</th>
						<th class="text-left font-semibold p-3 w-44">Event type</th>
						<th class="text-left font-semibold p-3 w-32">Domain</th>
						<th class="text-left font-semibold p-3 w-32">Last reminded</th>
						<th class="w-28 p-3"></th>
					</tr>
				</thead>
				<tbody class="divide-y divide-surface-200-800">
					{#each visible as n (n.id)}
						<NotificationRow
							{n}
							selected={selected.has(n.id)}
							objectFixed={fixed.has(n.objectId)}
							onToggleSelect={() => (selected = toggleIn(selected, n.id))}
							onOpen={() => openNotification(n)}
							onToggleRead={() => setRead([n.id], !n.isRead)}
							onDelete={() => remove([n.id])}
							onToggleFixed={() => (fixed = toggleIn(fixed, n.objectId))}
						/>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	<div class="card bg-surface-50-950 shadow-sm p-3 text-xs text-surface-600-400">
		<p class="font-semibold text-surface-800-200 mb-2">What this mock is trying to settle</p>
		<ul class="list-disc ml-5 space-y-1">
			<li>
				<strong>The dedupe collapse.</strong> "reminded 30× since 15 Aug" is <em>one row</em>, not
				thirty. That one write-path rule is where nearly all the volume reduction lives.
			</li>
			<li>
				<strong>Read as the suppression latch.</strong> Mark a still-true reminder read, run the sweep,
				and it does not come back. That is what makes clearing the inbox work.
			</li>
			<li>
				<strong>Auto-clear without vanishing.</strong> Fix an object, sweep, and the row marks itself
				read with a "no longer applies" chip — the badge drops but nothing silently disappears.
			</li>
			<li>
				<strong>Attestation lives on the object.</strong> The policy row links out to where the acknowledgement
				is recorded instead of pretending an inbox click is evidence.
			</li>
			<li>
				<strong>Per-object rows, not digests.</strong> Three expiring evidences are three rows,
				which is what makes click-to-object universal and per-row actions meaningful — at the cost
				of volume. <em>Does a flat table still hold up at a realistic overdue count?</em> That is
				the open question, and the reason this is deliberately un-grouped the way
				<code>ModelTable</code> would render it.
			</li>
		</ul>
	</div>
</div>
