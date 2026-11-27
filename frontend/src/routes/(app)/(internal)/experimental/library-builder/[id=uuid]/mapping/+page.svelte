<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { pageTitle } from '#lib/utils/stores.js';
	import { m } from '#paraglide/messages.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { getToastStore } from '#lib/components/Toast/stores.js';

	interface Node {
		urn: string;
		ref_id: string;
		name: string;
		description: string;
		parent: string;
	}
	interface Pair {
		source_requirement_urn: string;
		target_requirement_urn: string;
		relationship: string;
		reworded?: boolean;
		[key: string]: unknown;
	}
	interface Suggestion {
		source: string;
		target: string;
		relationship: string;
		reason: 'urn' | 'ref_id' | 'name' | 'mapping' | 'via';
		via?: string;
		reworded: boolean;
	}
	type Op = { op: 'add' | 'update' | 'remove'; source: string; target: string } & Record<
		string,
		unknown
	>;

	const toastStore = getToastStore();
	let { data } = $props();
	const editor = data.editor;
	const setUrn: string = editor.set.urn;
	const draftBase = `/experimental/library-builder/${data.draftId}`;

	$pageTitle = m.lbMappingPageTitle({ name: editor.set.name || editor.set.ref_id });

	const sourceNodes: Node[] = editor.source.nodes;
	const targetNodes: Node[] = editor.target.nodes;
	const targetByUrn = new Map(targetNodes.map((n) => [n.urn, n]));
	const CYCLE = ['intersect', 'equal', 'subset', 'superset'];
	const RELATIONSHIPS = [...CYCLE, 'not_related'];
	const REL_STYLE: Record<string, string> = {
		equal: 'preset-filled-success-500',
		intersect: 'preset-filled-primary-500',
		subset: 'preset-filled-tertiary-500',
		superset: 'preset-filled-secondary-500',
		not_related: 'preset-filled-surface-500'
	};
	const REASON_LABEL: Record<Suggestion['reason'], (s: Suggestion) => string> = {
		urn: () => m.lbMappingReasonUrn(),
		ref_id: () => m.lbMappingReasonRefId(),
		name: () => m.lbMappingReasonName(),
		mapping: (s) => m.lbMappingReasonMapping({ name: s.via ?? '' }),
		via: (s) => m.lbMappingReasonVia({ name: s.via ?? '' })
	};

	const key = (source: string, target: string) => `${source}|${target}`;
	let pairs: Map<string, Pair> = $state(
		new Map(
			(editor.pairs as Pair[]).map((p) => [
				key(p.source_requirement_urn.toLowerCase(), p.target_requirement_urn.toLowerCase()),
				p
			])
		)
	);
	let suggestions: Suggestion[] = $state(editor.suggestions);
	// Wording hints: [target urn, score][] per source, best first.
	const hints: Record<string, [string, number][]> = editor.hints ?? {};
	interface Issue {
		code: 'pairConflict' | 'pairDuplicate' | 'pairNodeMissing' | 'equalFanOut' | 'reverseConflict';
		source: string | null;
		target: string | null;
		detail: string[];
	}
	let issues: Issue[] = $state(editor.issues ?? []);
	const sourceByUrn = new Map(sourceNodes.map((n) => [n.urn, n]));
	let reverse: { urn: string; in_sync: boolean } | null = $state(editor.reverse);
	let defaultRelationship = $state('intersect');

	let pairsBySource = $derived.by(() => {
		const grouped = new Map<string, Pair[]>();
		for (const p of pairs.values()) {
			const list = grouped.get(p.source_requirement_urn) ?? [];
			list.push(p);
			grouped.set(p.source_requirement_urn, list);
		}
		return grouped;
	});
	let suggestionsBySource = $derived.by(() => {
		const grouped = new Map<string, Suggestion[]>();
		for (const s of suggestions) grouped.set(s.source, [...(grouped.get(s.source) ?? []), s]);
		return grouped;
	});
	let issuesBySource = $derived.by(() => {
		const grouped = new Map<string, Issue[]>();
		for (const issue of issues) {
			// A target equal to several sources concerns each of those rows.
			const rows = issue.source ? [issue.source] : issue.detail;
			for (const urn of rows) grouped.set(urn, [...(grouped.get(urn) ?? []), issue]);
		}
		return grouped;
	});
	const nodeLabel = (urn: string | null) => {
		const node = urn ? (sourceByUrn.get(urn) ?? targetByUrn.get(urn)) : undefined;
		return node?.ref_id || urn?.split(':').at(-1) || '';
	};
	function issueText(issue: Issue): string {
		const detail = issue.detail
			.map((d) =>
				issue.code === 'equalFanOut' || issue.code === 'pairNodeMissing'
					? issue.code === 'pairNodeMissing'
						? d === 'source'
							? m.lbMappingSourceSide()
							: m.lbMappingTargetSide()
						: nodeLabel(d)
					: safeTranslate(d === 'not_related' ? 'notRelated' : d)
			)
			.join(', ');
		const pair = `${nodeLabel(issue.source)} → ${nodeLabel(issue.target)}`;
		switch (issue.code) {
			case 'pairConflict':
				return m.lbMappingIssueConflict({ pair, detail });
			case 'pairDuplicate':
				return m.lbMappingIssueDuplicate({ pair });
			case 'pairNodeMissing':
				return m.lbMappingIssueMissing({ pair, detail });
			case 'equalFanOut':
				return m.lbMappingIssueEqualFanOut({
					item: nodeLabel(issue.source ?? issue.target),
					detail
				});
			case 'reverseConflict':
				return m.lbMappingIssueReverse({
					pair,
					here: safeTranslate(issue.detail[0]),
					there: safeTranslate(issue.detail[1])
				});
		}
	}
	const ISSUE_ERRORS = new Set(['pairConflict', 'pairNodeMissing', 'reverseConflict']);
	// Links to an item deleted from its framework have no row to remove them
	// from. Not undoable: the server refuses to re-add a link to a missing item.
	let danglingIssues = $derived(issues.filter((i) => i.code === 'pairNodeMissing'));
	function removeDangling() {
		for (const issue of danglingIssues) {
			if (issue.source && issue.target)
				applyLocal({ op: 'remove', source: issue.source, target: issue.target });
		}
		issues = issues.filter((i) => i.code !== 'pairNodeMissing');
	}
	let issuesOnly = $state(false);
	let mappedCount = $derived(sourceNodes.filter((n) => pairsBySource.has(n.urn)).length);

	// --- Filtering --------------------------------------------------------------
	let search = $state('');
	let unmappedOnly = $state(false);
	// shortcut: rows render in pages of PAGE_SIZE, no virtualization; enough for SCF-sized sets.
	const PAGE_SIZE = 200;
	let limit = $state(PAGE_SIZE);

	const haystack = (n: Node) => `${n.ref_id} ${n.name} ${n.description}`.toLowerCase();
	function matches(n: Node, needle: string): boolean {
		const text = haystack(n);
		return needle.split(/\s+/).every((token) => text.includes(token));
	}

	let filteredRows = $derived.by(() => {
		const needle = search.trim().toLowerCase();
		return sourceNodes.filter(
			(n) =>
				(!unmappedOnly || !pairsBySource.has(n.urn)) &&
				(!issuesOnly || issuesBySource.has(n.urn)) &&
				(!needle || matches(n, needle))
		);
	});
	let rows = $derived(filteredRows.slice(0, limit));
	let active = $state(0);
	let activeUrn = $derived(rows[Math.min(active, rows.length - 1)]?.urn);

	// --- Saving: local apply, queued ops, debounced flush -------------------------
	let queue: Op[] = [];
	let flushTimer: ReturnType<typeof setTimeout> | undefined;
	let saving = $state(false);
	let pendingCount = $state(0);
	let inFlight: Promise<void> | null = null;
	// Bumped on every local edit: tells a reverse generation whether edits
	// landed while it ran.
	let editCount = 0;
	let connectionLost = false;
	let undoStack: { ops: Op[]; restore: Suggestion[] }[] = $state([]);

	function setStatus(message: string, type: 'success' | 'error') {
		toastStore.trigger({
			message,
			background: type === 'error' ? 'preset-filled-error-500' : 'preset-filled-success-500'
		});
	}

	function applyLocal(op: Op) {
		const k = key(op.source, op.target);
		const { op: kind, source, target, ...fields } = op;
		if (kind === 'remove') {
			pairs.delete(k);
		} else {
			const current = pairs.get(k) ?? {
				source_requirement_urn: source,
				target_requirement_urn: target,
				relationship: 'intersect'
			};
			pairs.set(k, { ...current, ...fields } as Pair);
		}
		pairs = new Map(pairs);
		editCount += 1;
		queue.push(op);
		pendingCount = queue.length;
		if (reverse) reverse = { ...reverse, in_sync: false };
		clearTimeout(flushTimer);
		flushTimer = setTimeout(flush, 600);
	}

	function flush(): Promise<void> {
		clearTimeout(flushTimer);
		if (inFlight) return inFlight;
		if (queue.length === 0) return Promise.resolve();
		inFlight = saveBatch().finally(() => {
			inFlight = null;
			if (queue.length && !connectionLost) flush();
		});
		return inFlight;
	}

	async function saveBatch() {
		const ops = queue;
		queue = [];
		saving = true;
		try {
			let res: Response;
			try {
				res = await fetch(draftBase, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ action: 'edit-mapping-pairs', set_urn: setUrn, ops })
				});
			} catch {
				// Never reached the server, or its answer was lost. Every op is
				// idempotent (add upserts, remove ignores absent pairs), so the
				// batch goes back in front of the queue and is sent again.
				queue = [...ops, ...queue];
				if (!connectionLost) setStatus(m.lbMappingSaveRetrying(), 'error');
				connectionLost = true;
				flushTimer = setTimeout(() => ((connectionLost = false), flush()), 5000);
				return;
			}
			connectionLost = false;
			if (!res.ok) {
				const result = await res.json().catch(() => ({}));
				// The batch was rejected as a whole: the local view is now ahead of the draft.
				setStatus(`${m.lbMappingSaveFailed()} ${safeTranslate(result.error ?? '')}`, 'error');
				window.location.reload();
				return;
			}
			const result = await res.json().catch(() => ({}));
			if (Array.isArray(result.issues)) issues = result.issues;
		} finally {
			saving = false;
			pendingCount = queue.length;
		}
	}

	/** Resolves once every queued edit is saved; false if the connection is down. */
	async function settle(): Promise<boolean> {
		while (inFlight || queue.length) {
			await flush();
			if (connectionLost) return false;
		}
		return true;
	}

	function inverseOf(op: Op): Op {
		const k = key(op.source, op.target);
		const prior = pairs.get(k);
		if (!prior) return { op: 'remove', source: op.source, target: op.target };
		const { source_requirement_urn, target_requirement_urn, reworded, ...fields } = prior;
		return {
			op: op.op === 'remove' ? 'add' : 'update',
			source: op.source,
			target: op.target,
			...fields
		};
	}

	/** One user action = one undo step. */
	function commit(ops: Op[], restore: Suggestion[] = []) {
		const inverse = ops.map(inverseOf).reverse();
		ops.forEach(applyLocal);
		undoStack = [...undoStack, { ops: inverse, restore }];
	}

	function undo() {
		const step = undoStack.at(-1);
		if (!step) return;
		undoStack = undoStack.slice(0, -1);
		step.ops.forEach(applyLocal);
		if (step.restore.length) suggestions = [...suggestions, ...step.restore];
	}

	// --- Actions ------------------------------------------------------------------
	function addTarget(source: string, target: string) {
		if (pairs.has(key(source, target))) return;
		commit([{ op: 'add', source, target, relationship: defaultRelationship }]);
	}

	function cycle(pair: Pair) {
		const next = CYCLE[(CYCLE.indexOf(pair.relationship) + 1) % CYCLE.length];
		commit([
			{
				op: 'update',
				source: pair.source_requirement_urn,
				target: pair.target_requirement_urn,
				relationship: next
			}
		]);
	}

	function remove(pair: Pair) {
		commit([
			{ op: 'remove', source: pair.source_requirement_urn, target: pair.target_requirement_urn }
		]);
	}

	function accept(list: Suggestion[]) {
		if (!list.length) return;
		const accepted = new Set(list);
		suggestions = suggestions.filter((s) => !accepted.has(s));
		commit(
			list.map((s) => ({
				op: 'add',
				source: s.source,
				target: s.target,
				relationship: s.relationship
			})),
			list
		);
		// The reworded flag travels with the pair until the next reload recomputes it.
		for (const s of list) {
			const pair = pairs.get(key(s.source, s.target));
			if (pair) pairs.set(key(s.source, s.target), { ...pair, reworded: s.reworded });
		}
		pairs = new Map(pairs);
	}

	function dismiss(s: Suggestion) {
		suggestions = suggestions.filter((x) => x !== s);
	}

	let generatingReverse = $state(false);
	async function generateReverse() {
		generatingReverse = true;
		try {
			// The reverse is derived from the saved set: every edit must be in first.
			if (!(await settle())) return;
			const editsBefore = editCount;
			const res = await fetch(draftBase, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ action: 'generate-reverse-set', set_urn: setUrn })
			});
			const result = await res.json().catch(() => ({}));
			if (!res.ok) return setStatus(safeTranslate(result.error ?? 'error'), 'error');
			// An edit made while this ran is not in the generated set.
			reverse = { urn: result.urn, in_sync: editCount === editsBefore };
			if (Array.isArray(result.issues)) issues = result.issues;
			setStatus(m.lbMappingReverseGenerated({ count: result.count }), 'success');
		} catch {
			setStatus(m.lbMappingSaveRetrying(), 'error');
		} finally {
			generatingReverse = false;
		}
	}

	// --- Target autocomplete (active row only) -----------------------------------
	let query = $state('');
	let highlighted = $state(0);
	let searchInput: HTMLInputElement | undefined = $state();
	let targetInput: HTMLInputElement | undefined = $state();

	let targetFocused = $state(false);
	// With nothing typed, the closest wordings of the active row (hints only).
	let hinted = $derived(
		targetFocused && !query.trim() && activeUrn
			? (hints[activeUrn] ?? [])
					.filter(([urn]) => !pairs.has(key(activeUrn, urn)))
					.map(([urn]) => targetByUrn.get(urn))
					.filter((n): n is Node => Boolean(n))
			: []
	);
	let candidates = $derived.by(() => {
		const needle = query.trim().toLowerCase();
		if (!needle) return hinted;
		const hits = targetNodes.filter((n) => matches(n, needle));
		// ref_id prefix hits first: typing "a.5" should land on A.5.x.
		hits.sort(
			(a, b) =>
				Number(!a.ref_id.toLowerCase().startsWith(needle)) -
				Number(!b.ref_id.toLowerCase().startsWith(needle))
		);
		return hits.slice(0, 8);
	});

	function onTargetKey(event: KeyboardEvent, source: string) {
		if (event.key === 'ArrowDown') {
			highlighted = Math.min(highlighted + 1, candidates.length - 1);
		} else if (event.key === 'ArrowUp') {
			highlighted = Math.max(highlighted - 1, 0);
		} else if (event.key === 'Enter' && candidates[highlighted]) {
			addTarget(source, candidates[highlighted].urn);
			query = '';
		} else if (event.key === 'Escape') {
			query = '';
			targetInput?.blur();
		} else {
			return;
		}
		event.preventDefault();
	}

	async function focusTarget() {
		await tick();
		targetInput?.focus();
	}

	async function moveTo(index: number) {
		active = Math.max(0, Math.min(index, rows.length - 1));
		query = '';
		await tick();
		document.getElementById(`row-${active}`)?.scrollIntoView({ block: 'nearest' });
	}

	function onWindowKey(event: KeyboardEvent) {
		if ((event.metaKey || event.ctrlKey) && event.key === 'z') {
			event.preventDefault();
			undo();
			return;
		}
		const target = event.target as HTMLElement;
		if (target.closest('input, select, textarea, button, a, [contenteditable]')) return;
		const handlers: Record<string, () => void> = {
			j: () => moveTo(active + 1),
			ArrowDown: () => moveTo(active + 1),
			k: () => moveTo(active - 1),
			ArrowUp: () => moveTo(active - 1),
			'/': () => searchInput?.focus(),
			Enter: () => focusTarget(),
			a: () => {
				if (activeUrn) accept(suggestionsBySource.get(activeUrn) ?? []);
			}
		};
		const handler = handlers[event.key];
		if (handler) {
			event.preventDefault();
			handler();
		}
	}

	function label(node: Node | undefined, fallback: string): string {
		return node ? node.ref_id || node.name || fallback : fallback;
	}

	function tooltip(node: Node | undefined): string {
		return node ? [node.ref_id, node.name, node.description].filter(Boolean).join(' — ') : '';
	}

	onMount(() => {
		const beforeUnload = (event: BeforeUnloadEvent) => {
			if (queue.length || saving) event.preventDefault();
		};
		window.addEventListener('beforeunload', beforeUnload);
		return () => window.removeEventListener('beforeunload', beforeUnload);
	});
</script>

<svelte:window onkeydown={onWindowKey} />

<div class="space-y-4">
	<div class="card p-4 space-y-3">
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div class="flex items-center gap-2 min-w-0">
				<a href={draftBase} class="text-surface-500 hover:text-surface-700" aria-label={m.back()}>
					<i class="fa-solid fa-arrow-left"></i>
				</a>
				<div class="min-w-0">
					<h2 class="text-xl font-semibold truncate">{editor.set.name || editor.set.ref_id}</h2>
					<p class="text-sm text-surface-500 truncate">
						{editor.source.name}
						<i class="fa-solid fa-arrow-right mx-1"></i>
						{editor.target.name}
					</p>
				</div>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<span class="text-sm text-surface-500" aria-live="polite">
					{#if saving || pendingCount}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>{m.saving()}
					{:else}
						<i class="fa-solid fa-check mr-1 text-success-500"></i>{m.lbMappingSaved()}
					{/if}
				</span>
				<button
					type="button"
					class="btn btn-sm preset-outlined-surface-500"
					onclick={undo}
					disabled={!undoStack.length}
					title="Ctrl+Z"
				>
					<i class="fa-solid fa-rotate-left mr-1"></i>{m.undo()}
				</button>
				<button
					type="button"
					class="btn btn-sm preset-outlined-primary-500"
					onclick={generateReverse}
					disabled={generatingReverse || (reverse?.in_sync ?? false)}
					title={m.lbMappingReverseHelp()}
				>
					{#if generatingReverse}<i class="fa-solid fa-spinner fa-spin mr-1"></i>{:else}<i
							class="fa-solid fa-right-left mr-1"
						></i>{/if}
					{!reverse
						? m.lbMappingGenerateReverse()
						: reverse.in_sync
							? m.lbMappingReverseInSync()
							: m.lbMappingRegenerateReverse()}
				</button>
			</div>
		</div>

		<div class="flex flex-wrap items-center gap-3">
			<div class="text-sm font-medium">
				{m.lbMappingProgress({ mapped: mappedCount, total: sourceNodes.length })}
			</div>
			<progress
				class="progress w-40"
				value={mappedCount}
				max={sourceNodes.length || 1}
				aria-label={m.lbMappingProgress({ mapped: mappedCount, total: sourceNodes.length })}
			></progress>
			<input
				bind:this={searchInput}
				class="input input-sm w-64 placeholder:text-surface-500"
				type="search"
				bind:value={search}
				oninput={() => ((limit = PAGE_SIZE), (active = 0))}
				placeholder={m.lbMappingSearchPlaceholder()}
				aria-label={m.search()}
			/>
			<label class="flex items-center gap-2 text-sm">
				<input type="checkbox" class="checkbox" bind:checked={unmappedOnly} />
				{m.lbMappingUnmappedOnly()}
			</label>
			{#if issues.length || issuesOnly}
				<label class="flex items-center gap-2 text-sm">
					<input
						type="checkbox"
						class="checkbox"
						bind:checked={issuesOnly}
						oninput={() => ((limit = PAGE_SIZE), (active = 0))}
					/>
					{m.lbMappingIssuesOnly()}
				</label>
			{/if}
			<label class="flex items-center gap-2 text-sm">
				{m.lbMappingDefaultRelationship()}
				<select class="select select-sm w-36" bind:value={defaultRelationship}>
					{#each RELATIONSHIPS as rel}
						<option value={rel}>{safeTranslate(rel === 'not_related' ? 'notRelated' : rel)}</option>
					{/each}
				</select>
			</label>
			{#if suggestions.length}
				<button
					type="button"
					class="btn btn-sm preset-filled-success-500 ml-auto"
					onclick={() => accept(suggestions)}
				>
					<i class="fa-solid fa-check-double mr-1"></i>
					{m.lbMappingAcceptAll({ count: suggestions.length })}
				</button>
			{/if}
		</div>
		{#if issues.length}
			{@const errorCount = issues.filter((i) => ISSUE_ERRORS.has(i.code)).length}
			<details
				class="rounded-md border p-2 text-sm {errorCount
					? 'border-error-500 bg-error-50 dark:bg-error-500/10'
					: 'border-warning-500 bg-warning-50 dark:bg-warning-500/10'}"
				open={errorCount > 0}
			>
				<summary class="cursor-pointer font-medium">
					<i class="fa-solid fa-triangle-exclamation mr-1"></i>
					{m.lbMappingIssuesSummary({ count: issues.length })}
				</summary>
				<ul class="mt-2 space-y-0.5 max-h-48 overflow-auto">
					{#each issues as issue}
						<li class={ISSUE_ERRORS.has(issue.code) ? 'text-error-700 dark:text-error-300' : ''}>
							{issueText(issue)}
						</li>
					{/each}
				</ul>
				{#if danglingIssues.length}
					<button
						type="button"
						class="btn btn-sm preset-filled-error-500 mt-2"
						onclick={removeDangling}
					>
						<i class="fa-solid fa-link-slash mr-1"></i>
						{m.lbMappingRemoveDangling({ count: danglingIssues.length })}
					</button>
				{/if}
			</details>
		{/if}
		<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-surface-600-400">
			<span class="flex items-center gap-1.5">
				<span class="badge preset-filled-primary-500 text-xs">{m.lbMappingLegendLink()}</span>
				{m.lbMappingLegendLinkHelp()}
			</span>
			<span class="flex items-center gap-1.5">
				<span
					class="badge border border-dashed border-success-500 text-success-700 dark:text-success-300 text-xs"
					>{m.lbMappingLegendSuggestion()}
					<i class="fa-solid fa-check ml-1"></i><i class="fa-solid fa-xmark"></i></span
				>
				{m.lbMappingLegendSuggestionHelp()}
			</span>
			<span><i class="fa-solid fa-link mr-1"></i>{m.lbMappingLegendChained()}</span>
			<span><i class="fa-solid fa-triangle-exclamation mr-1"></i>{m.lbMappingReworded()}</span>
		</div>
		<p class="text-xs text-surface-500">{m.lbMappingKeyboardHelp()}</p>
	</div>

	<div class="card divide-y divide-surface-200-800">
		{#each rows as node, index (node.urn)}
			{@const rowPairs = pairsBySource.get(node.urn) ?? []}
			{@const rowSuggestions = suggestionsBySource.get(node.urn) ?? []}
			<!-- row selection also has keyboard bindings (j/k), see onWindowKey -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				id="row-{index}"
				class="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-3 p-3 {node.urn ===
				activeUrn
					? 'bg-primary-50 dark:bg-primary-500/10'
					: ''}"
				onclick={() => (active = index)}
			>
				<div class="min-w-0" title={node.description}>
					{#if node.parent}<p class="text-xs text-surface-500 truncate">{node.parent}</p>{/if}
					<p class="text-sm">
						{#if issuesBySource.get(node.urn)?.length}
							{@const rowIssues = issuesBySource.get(node.urn) ?? []}
							<i
								class="fa-solid fa-triangle-exclamation {rowIssues.some((i) =>
									ISSUE_ERRORS.has(i.code)
								)
									? 'text-error-500'
									: 'text-warning-500'}"
								title={rowIssues.map(issueText).join('\n')}
							></i>
						{/if}
						<span class="font-mono font-semibold">{node.ref_id}</span>
						{#if node.name}{node.name}{:else}<span class="text-surface-600-400"
								>{node.description}</span
							>{/if}
					</p>
					{#if node.name && node.description && node.urn === activeUrn}
						<p class="text-xs text-surface-600-400 mt-1 whitespace-pre-line line-clamp-4">
							{node.description}
						</p>
					{/if}
				</div>
				<div class="flex flex-wrap items-center gap-1.5 min-w-0">
					{#each rowPairs as pair (pair.target_requirement_urn)}
						{@const target = targetByUrn.get(pair.target_requirement_urn)}
						<span class="badge {REL_STYLE[pair.relationship] ?? ''} gap-1 text-xs">
							<button
								type="button"
								class="flex items-center gap-1"
								title="{tooltip(target)} · {m.lbMappingCycleHelp()}"
								onclick={() => cycle(pair)}
							>
								{#if pair.reworded}<i
										class="fa-solid fa-triangle-exclamation"
										title={m.lbMappingReworded()}
									></i>{/if}
								<span class="font-mono">{label(target, pair.target_requirement_urn)}</span>
								<span class="opacity-75"
									>{safeTranslate(
										pair.relationship === 'not_related' ? 'notRelated' : pair.relationship
									)}</span
								>
							</button>
							<button
								type="button"
								class="ml-1 opacity-75 hover:opacity-100"
								aria-label={m.lbMappingRemovePair()}
								onclick={() => remove(pair)}
							>
								<i class="fa-solid fa-xmark"></i>
							</button>
						</span>
					{/each}
					{#each rowSuggestions as suggestion (suggestion.target)}
						{@const target = targetByUrn.get(suggestion.target)}
						<span
							class="badge border border-dashed border-success-500 text-success-700 dark:text-success-300 gap-1 text-xs"
							title="{m.lbMappingLegendSuggestion()} · {tooltip(target)} · {REASON_LABEL[
								suggestion.reason
							](suggestion)}"
						>
							{#if suggestion.reworded}<i
									class="fa-solid fa-triangle-exclamation"
									title={m.lbMappingReworded()}
								></i>{/if}
							<span class="font-mono">{label(target, suggestion.target)}</span>
							<span class="opacity-75"
								>{safeTranslate(
									suggestion.relationship === 'not_related' ? 'notRelated' : suggestion.relationship
								)}</span
							>
							{#if suggestion.reason === 'via'}<i
									class="fa-solid fa-link opacity-60"
									aria-hidden="true"
								></i>{/if}
							<button
								type="button"
								class="ml-1"
								aria-label={m.lbMappingAcceptSuggestion()}
								onclick={() => accept([suggestion])}
							>
								<i class="fa-solid fa-check"></i>
							</button>
							<button
								type="button"
								aria-label={m.lbMappingDismissSuggestion()}
								onclick={() => dismiss(suggestion)}
							>
								<i class="fa-solid fa-xmark"></i>
							</button>
						</span>
					{/each}
					{#if node.urn === activeUrn}
						<div class="relative min-w-48 flex-1">
							<input
								bind:this={targetInput}
								class="input input-sm placeholder:text-surface-500"
								type="text"
								bind:value={query}
								oninput={() => (highlighted = 0)}
								onkeydown={(e) => onTargetKey(e, node.urn)}
								onfocus={() => ((targetFocused = true), (highlighted = 0))}
								onblur={() => (targetFocused = false)}
								placeholder={m.lbMappingAddTargetPlaceholder()}
								aria-label={m.lbMappingAddTargetPlaceholder()}
								role="combobox"
								aria-expanded={candidates.length > 0}
								aria-controls="target-candidates"
							/>
							{#if candidates.length}
								<ul
									id="target-candidates"
									role="listbox"
									class="absolute z-20 mt-1 w-full max-h-72 overflow-auto card shadow-lg p-1"
								>
									{#if !query.trim()}
										<li class="px-2 pt-1 text-xs text-surface-500" role="presentation">
											<i class="fa-solid fa-lightbulb mr-1"></i>{m.lbMappingWordingHints()}
										</li>
									{/if}
									{#each candidates as candidate, i (candidate.urn)}
										<li role="option" aria-selected={i === highlighted}>
											<button
												type="button"
												class="w-full text-left text-sm px-2 py-1 rounded {i === highlighted
													? 'bg-primary-100 dark:bg-primary-500/20'
													: ''}"
												title={candidate.description}
												onmousedown={(e) => {
													e.preventDefault();
													addTarget(node.urn, candidate.urn);
													query = '';
												}}
											>
												<span class="font-mono font-semibold">{candidate.ref_id}</span>
												<span class={candidate.name ? '' : 'text-surface-600-400'}
													>{(candidate.name || candidate.description).slice(0, 140)}</span
												>
												{#if pairs.has(key(node.urn, candidate.urn))}
													<i class="fa-solid fa-check text-success-500 ml-1"></i>
												{/if}
											</button>
										</li>
									{/each}
								</ul>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		{:else}
			<p class="p-6 text-center text-sm text-surface-500">{m.lbMappingNoRows()}</p>
		{/each}
		{#if filteredRows.length > limit}
			<div class="p-3 text-center">
				<button
					type="button"
					class="btn btn-sm preset-outlined-surface-500"
					onclick={() => (limit += PAGE_SIZE)}
				>
					{m.lbMappingShowMore({ count: filteredRows.length - limit })}
				</button>
			</div>
		{/if}
	</div>
</div>
