<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import BellPopover from './BellPopover.svelte';
	import {
		CATEGORY_META,
		EVENT_TYPES,
		NOTIFICATIONS,
		SEVERITY_META,
		categoryOf,
		type Category,
		type Notif
	} from './fixtures';
	import { NOW, relTime, shortDate } from './time';

	$pageTitle = 'Notification centre (mock)';

	let items = $state<Notif[]>(NOTIFICATIONS.map((n) => ({ ...n })));
	/** dedupe keys whose underlying object the user has "fixed" — drives the sweep demo */
	let fixed = $state<Set<string>>(new Set());
	let selected = $state<Set<string>>(new Set());
	let view = $state<'unread' | 'all' | 'cleared'>('unread');
	let category = $state<Category | 'all'>('all');
	let eventType = $state<string | 'all'>('all');
	let search = $state('');
	let sweepLog = $state<string[]>([]);
	let toast = $state('');

	const unreadCount = $derived(items.filter((i) => !i.isRead).length);
	const clearedCount = $derived(items.filter((i) => i.autoCleared).length);

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
				view === 'unread' ? !i.isRead : view === 'cleared' ? Boolean(i.autoCleared) : true
			)
			.filter((i) => (category === 'all' ? true : categoryOf(i) === category))
			.filter((i) => (eventType === 'all' ? true : i.type === eventType))
			.filter((i) =>
				search.trim()
					? (i.title + i.body).toLowerCase().includes(search.trim().toLowerCase())
					: true
			)
			.sort((a, b) => {
				const at = new Date(a.lastSeenAt ?? a.createdAt).getTime();
				const bt = new Date(b.lastSeenAt ?? b.createdAt).getTime();
				return bt - at;
			})
	);

	const allVisibleSelected = $derived(
		visible.length > 0 && visible.every((i) => selected.has(i.id))
	);

	function toggle(id: string) {
		const next = new Set(selected);
		next.has(id) ? next.delete(id) : next.add(id);
		selected = next;
	}

	function toggleAll() {
		selected = allVisibleSelected ? new Set() : new Set(visible.map((i) => i.id));
	}

	function setRead(ids: string[], isRead: boolean) {
		items = items.map((i) =>
			ids.includes(i.id) ? { ...i, isRead, autoCleared: isRead ? i.autoCleared : false } : i
		);
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

	function toggleFixed(id: string) {
		const next = new Set(fixed);
		next.has(id) ? next.delete(id) : next.add(id);
		fixed = next;
	}

	/**
	 * The whole design in one button: read rows are never reopened while the condition
	 * holds, a cleared condition marks the row read itself, and a re-broken condition
	 * produces a fresh unread row.
	 */
	function runSweep() {
		const log: string[] = [];
		const next: Notif[] = [];
		for (const i of items) {
			if (!i.conditionBacked) {
				next.push(i);
				continue;
			}
			const stillTrue = !fixed.has(i.id);
			if (!stillTrue) {
				if (!i.autoCleared) {
					next.push({ ...i, isRead: true, autoCleared: true });
					log.push(`✓ "${i.title}" — condition gone, marked read and key re-armed`);
				} else {
					next.push(i);
				}
				continue;
			}
			if (i.autoCleared) {
				next.push({
					...i,
					isRead: false,
					autoCleared: false,
					seenCount: 1,
					createdAt: new Date(NOW).toISOString(),
					lastSeenAt: new Date(NOW).toISOString()
				});
				log.push(`↻ "${i.title}" — broke again, key was armed, fired as a new unread row`);
				continue;
			}
			const bumped = {
				...i,
				seenCount: (i.seenCount ?? 1) + 1,
				lastSeenAt: new Date(NOW).toISOString()
			};
			next.push(bumped);
			log.push(
				i.isRead
					? `· "${i.title}" — still true but read, suppressed (no reopen)`
					: `· "${i.title}" — still true, reminder count now ${bumped.seenCount}`
			);
		}
		items = next;
		sweepLog = log;
	}

	function reset() {
		items = NOTIFICATIONS.map((n) => ({ ...n }));
		fixed = new Set();
		selected = new Set();
		sweepLog = [];
	}
</script>

<div class="flex flex-col gap-4 p-4">
	<!-- Framing -->
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
			acknowledgement
			<em>and</em> the thing that stops the reminder.
		</span>
	</div>

	<!-- Surface 1: the AppBar bell, reproduced here since this page can't inject into the real one -->
	<div class="card bg-surface-50-950 shadow-sm p-3">
		<div class="flex items-center justify-between gap-3">
			<span class="text-xs text-surface-500">
				<i class="fa-solid fa-arrow-right mr-1"></i>
				Surface 1 — the bell, as it would sit in the app bar next to the theme toggle:
			</span>
			<div class="flex items-center gap-2">
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
	</div>

	<!-- The sweep simulator: the part that is hard to convey on paper -->
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
				got fixed, then run the sweep. Un-fix it and sweep again to see the key re-arm.
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
		<!-- Filters -->
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

		<!-- Batch bar -->
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

		<!-- List -->
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
								onchange={toggleAll}
								aria-label="Select all"
							/>
						</th>
						<th class="text-left font-semibold p-3">Notification</th>
						<th class="text-left font-semibold p-3 w-40">Category</th>
						<th class="text-left font-semibold p-3 w-32">Last reminded</th>
						<th class="w-28 p-3"></th>
					</tr>
				</thead>
				<tbody class="divide-y divide-surface-200-800">
					{#each visible as n (n.id)}
						{@const sev = SEVERITY_META[n.severity]}
						{@const isFixed = fixed.has(n.id)}
						<tr
							class="hover:bg-surface-100-900 transition-colors {n.isRead
								? 'bg-surface-50-950'
								: 'bg-primary-50/40 dark:bg-primary-950/30'}"
						>
							<td class="p-3 align-top">
								<input
									type="checkbox"
									class="checkbox"
									checked={selected.has(n.id)}
									onchange={() => toggle(n.id)}
									aria-label="Select notification"
								/>
							</td>
							<td class="p-3">
								<div class="flex gap-2.5">
									<span class="mt-1.5 size-2 shrink-0 rounded-full {sev.dot}"></span>
									<div class="min-w-0">
										<button
											class="text-left cursor-pointer {n.isRead
												? 'font-normal text-surface-700-300'
												: 'font-bold text-surface-900-100'}"
											onclick={() => openNotification(n)}
										>
											{n.title}
										</button>
										<p class="text-surface-500 mt-0.5">{n.body}</p>
										<div class="flex flex-wrap items-center gap-1.5 mt-1.5">
											<a
												href={n.link}
												class="text-primary-600 hover:underline"
												onclick={(e) => e.preventDefault()}
											>
												<i class="fa-solid fa-arrow-up-right-from-square mr-1 text-[10px]"
												></i>{n.linkLabel}
											</a>
											{#if n.attestation}
												<a
													href={n.attestation.link}
													class="px-2 py-0.5 rounded border border-primary-300 dark:border-primary-700 text-primary-700 dark:text-primary-300 hover:bg-primary-50 dark:hover:bg-primary-950"
													onclick={(e) => e.preventDefault()}
													title="The record lives on the object, never in the inbox"
												>
													{n.attestation.label} →
												</a>
											{/if}
											{#if n.seenCount && n.seenCount > 1}
												<span
													class="px-1.5 py-0.5 rounded bg-surface-100-900 border border-surface-200-800 text-surface-500"
													title="One row, upserted by every sweep — not {n.seenCount} rows"
												>
													reminded {n.seenCount}× since {shortDate(n.createdAt)}
												</span>
											{/if}
											{#if n.autoCleared}
												<span
													class="px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
													title="The sweep saw the condition go away and marked this read for you"
												>
													<i class="fa-solid fa-check mr-1"></i>no longer applies
												</span>
											{/if}
											{#if isFixed && !n.autoCleared}
												<span
													class="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
												>
													object fixed — clears on next sweep
												</span>
											{/if}
											{#if !n.conditionBacked}
												<span
													class="px-1.5 py-0.5 rounded bg-surface-100-900 border border-surface-200-800 text-surface-400"
												>
													event
												</span>
											{/if}
										</div>
									</div>
								</div>
							</td>
							<td class="p-3 align-top text-surface-600-400">
								<i class="fa-solid {CATEGORY_META[categoryOf(n)].icon} mr-1.5 text-surface-400"></i>
								<span class="block">{EVENT_TYPES[n.type].label}</span>
								<span class="block text-[10px] text-surface-400"
									>{CATEGORY_META[categoryOf(n)].label}</span
								>
							</td>
							<td class="p-3 align-top text-surface-500 whitespace-nowrap">
								{relTime(n.lastSeenAt ?? n.createdAt)}
							</td>
							<td class="p-3 align-top">
								<div class="flex items-center justify-end gap-1">
									{#if n.conditionBacked}
										<button
											class="size-7 rounded hover:bg-surface-200-800 text-surface-500 cursor-pointer {isFixed
												? 'text-amber-600'
												: ''}"
											title={isFixed
												? 'Un-fix the object'
												: 'Pretend the underlying object got fixed'}
											onclick={() => toggleFixed(n.id)}
										>
											<i class="fa-solid fa-wrench text-[11px]"></i>
										</button>
									{/if}
									<button
										class="size-7 rounded hover:bg-surface-200-800 text-surface-500 cursor-pointer"
										title={n.isRead ? 'Mark as unread — bring it back to me' : 'Mark as read'}
										onclick={() => setRead([n.id], !n.isRead)}
									>
										<i class="fa-solid {n.isRead ? 'fa-envelope' : 'fa-envelope-open'} text-[11px]"
										></i>
									</button>
									<button
										class="size-7 rounded hover:bg-error-100 dark:hover:bg-error-950 text-surface-500 hover:text-error-600 cursor-pointer"
										title="Delete — removes the message. If the condition still holds it returns tomorrow."
										onclick={() => remove([n.id])}
									>
										<i class="fa-solid fa-trash text-[11px]"></i>
									</button>
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	<!-- What to look at -->
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
				<strong>Does a flat table hold up?</strong> This is deliberately un-grouped, the way
				<code>ModelTable</code> would render it. If it reads fine at 12 rows, filters plus the dedupe
				collapse are probably enough and the bespoke grouped list can wait.
			</li>
		</ul>
	</div>
</div>
