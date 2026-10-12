<script lang="ts">
	// A computed metric started from instances: pick them, write a formula,
	// name it. The backend makes the definition (or reuses an identical one)
	// and the instance, pinned to the picks, in a domain holding them all.
	import { onMount, tick } from 'svelte';
	import { flip } from 'svelte/animate';
	import { goto } from '$app/navigation';
	import { m } from '$paraglide/messages';
	import CelInput from '$lib/components/Cel/CelInput.svelte';
	import { getModalStore, type ModalStore } from './stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import {
		datasetNameProblem,
		formulaKey,
		formulaScope,
		keepOrFirst,
		latestTrend,
		moveItem,
		sparkline,
		quickFormulas,
		renameReference,
		type QuickFormula,
		type SparkPoint
	} from '$lib/utils/derived-metrics';

	interface Candidate {
		id: string;
		name: string;
		folder: { id: string; str: string };
		frequency: string | null;
		current_value: string;
		definition: { id: string; name: string };
	}
	interface Picked extends Candidate {
		key: string;
	}
	interface Props {
		parent: any;
		// Instances to start with: a list selection, or the instance page.
		instanceIds?: string[];
	}

	let { parent, instanceIds = [] }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	const FREQUENCIES = [
		['realtime', () => m.realTimeContinuous()],
		['hourly', () => m.hourly()],
		['daily', () => m.daily()],
		['weekly', () => m.weekly()],
		['monthly', () => m.monthly()],
		['quarterly', () => m.quarterly()],
		['yearly', () => m.yearly()]
	] as const;
	const QUICK_LABELS: Record<QuickFormula, () => string> = {
		ratio: () => m.quickFormulaRatio(),
		difference: () => m.quickFormulaDifference(),
		sum: () => m.quickFormulaSum(),
		average: () => m.quickFormulaAverage()
	};

	let picked = $state<Picked[]>([]);
	let expression = $state('');
	let name = $state('');
	let domains = $state<{ id: string; str: string }[]>([]);
	let folder = $state('');
	let frequency = $state('monthly');
	let frequencyChosen = false;
	let units = $state<{ id: string; label: string }[]>([]);
	let unit = $state('');
	let target = $state('');
	let higherIsBetter = $state(true);
	let errors = $state<Record<string, string[]>>({});
	let saving = $state(false);
	let contextLoaded = $state(false);

	// ---------- picking ----------

	let searchInput = $state<HTMLInputElement | null>(null);
	let query = $state('');
	let results = $state<Candidate[]>([]);
	let resultsOpen = $state(false);
	let highlighted = $state(0);
	let searchSeq = 0;
	const offered = $derived(results.filter((r) => !picked.some((p) => p.id === r.id)));

	// What the results answer: Enter must never add a match for an older query.
	let resultsQuery: string | null = null;

	async function search() {
		const seq = ++searchSeq;
		const asked = query.trim();
		const params = new URLSearchParams();
		if (asked) params.set('search', asked);
		try {
			const res = await fetch(`/fe-api/metrology/compose-candidates?${params}`);
			const body = res.ok ? await res.json() : [];
			if (seq === searchSeq) {
				results = Array.isArray(body) ? body : [];
				resultsQuery = asked;
				highlighted = 0;
			}
		} catch {
			if (seq === searchSeq) results = [];
		}
	}
	$effect(() => {
		void query;
		if (!resultsOpen) return;
		const timer = setTimeout(search, 150);
		return () => clearTimeout(timer);
	});

	function add(candidate: Candidate) {
		const key = formulaKey(
			candidate.definition.name,
			picked.map((p) => p.key)
		);
		picked = [...picked, { ...candidate, key }];
		query = '';
		highlighted = 0;
		searchInput?.focus();
	}

	function remove(index: number) {
		picked = picked.filter((_, i) => i !== index);
	}

	// The order is the inputs' order in the definition, and the quick
	// formulas read it: the first pick is the ratio's numerator.
	let dragFrom = $state<number | null>(null);
	let dragOver = $state<number | null>(null);

	function endDrag() {
		dragFrom = null;
		dragOver = null;
	}

	async function moveWithKeys(event: KeyboardEvent, index: number) {
		const to = event.key === 'ArrowUp' ? index - 1 : event.key === 'ArrowDown' ? index + 1 : null;
		if (to === null || to < 0 || to >= picked.length) return;
		event.preventDefault();
		const id = picked[index].id;
		picked = moveItem(picked, index, to);
		await tick();
		modalEl?.querySelector<HTMLButtonElement>(`[data-handle="${id}"]`)?.focus();
	}

	function onSearchKeydown(event: KeyboardEvent) {
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			resultsOpen = true;
			highlighted = Math.min(highlighted + 1, offered.length - 1);
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			highlighted = Math.max(highlighted - 1, 0);
		} else if (event.key === 'Enter') {
			event.preventDefault();
			if (resultsQuery === query.trim()) {
				if (offered[highlighted]) add(offered[highlighted]);
				return;
			}
			// Typed faster than the search answered: answer it now, take the best match.
			resultsOpen = true;
			search().then(() => {
				if (resultsQuery === query.trim() && offered[0]) add(offered[0]);
			});
		} else if (event.key === 'Escape' && resultsOpen) {
			// A search field clears itself on Escape, which reads as typing and
			// would reopen the list: close it, and leave the text alone.
			event.preventDefault();
			event.stopPropagation();
			resultsOpen = false;
		}
	}

	// ---------- names in the formula ----------

	let renaming = $state<number | null>(null);
	let renameValue = $state('');
	let renameInput = $state<HTMLInputElement | null>(null);
	const renameProblem = $derived(
		renaming === null
			? null
			: datasetNameProblem(
					renameValue,
					picked.filter((_, i) => i !== renaming).map((p) => p.key)
				)
	);

	async function startRename(index: number) {
		renaming = index;
		renameValue = picked[index].key;
		await tick();
		renameInput?.select();
	}

	function commitRename() {
		if (renaming === null) return;
		const index = renaming;
		renaming = null;
		if (renameProblem) return;
		const from = picked[index].key;
		expression = renameReference(expression, from, renameValue);
		picked = picked.map((p, i) => (i === index ? { ...p, key: renameValue } : p));
	}

	function insert(key: string) {
		expression =
			expression && !expression.endsWith(' ') ? `${expression} ${key}` : `${expression}${key}`;
	}

	const keys = $derived(picked.map((p) => p.key));
	const quick = $derived(expression.trim() ? [] : quickFormulas(keys));
	const inputs = $derived(
		picked.map((p) => ({ key: p.key, definition: p.definition.id, combine: 'one' as const }))
	);
	const choices = $derived(Object.fromEntries(picked.map((p) => [p.key, { pick: p.id }])));

	// ---------- where it lives and how often ----------

	let contextSeq = 0;
	$effect(() => {
		const ids = picked.map((p) => p.id);
		const seq = ++contextSeq;
		if (!ids.length) {
			domains = [];
			contextLoaded = false;
			return;
		}
		const params = new URLSearchParams();
		for (const id of ids) params.append('instance', id);
		fetch(`/fe-api/metrology/compose-context?${params}`)
			.then((res) => (res.ok ? res.json() : null))
			.then((body) => {
				if (seq !== contextSeq || !body) return;
				domains = body.domains ?? [];
				folder = keepOrFirst(folder, domains);
				if (!frequencyChosen && body.frequency) frequency = body.frequency;
				contextLoaded = true;
			})
			.catch(() => {});
	});

	// ---------- the live result ----------

	let preview = $state<null | {
		ok: boolean;
		value?: unknown;
		periods?: {
			start: string;
			value: unknown;
			skipped: boolean;
			inputs?: Record<string, unknown>;
		}[];
		errors?: { code: string; message: string }[];
	}>(null);
	let previewBusy = $state(false);
	let previewSeq = 0;
	const celScope = $derived(formulaScope('metrics', null, inputs, preview));
	const recentPeriods = $derived([...(preview?.periods ?? [])].reverse().slice(0, 4));

	// The last year or so of periods, as a small chart under the value.
	const CHART = { width: 240, height: 64, periods: 12 };
	const chartId = $props.id();
	const chartPeriods = $derived((preview?.periods ?? []).slice(-CHART.periods));
	const chart = $derived(sparkline(chartPeriods, CHART.width, CHART.height, 6));
	const trend = $derived(latestTrend(chartPeriods, higherIsBetter));
	let hovered = $state<SparkPoint | null>(null);
	const unitLabel = $derived(units.find((u) => u.id === unit)?.label ?? '');

	async function runPreview() {
		const seq = ++previewSeq;
		previewBusy = true;
		try {
			const res = await fetch('/fe-api/metrology/preview-formula', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					folder,
					frequency,
					inputs,
					input_choices: choices,
					expression,
					category: 'quantitative'
				})
			});
			const body = await res.json();
			if (seq === previewSeq) preview = body;
		} catch {
			if (seq === previewSeq)
				preview = { ok: false, errors: [{ code: 'network', message: m.previewFailed() }] };
		} finally {
			if (seq === previewSeq) previewBusy = false;
		}
	}
	const previewKey = $derived(JSON.stringify([folder, frequency, inputs, choices, expression]));
	$effect(() => {
		void previewKey;
		if (!folder || !picked.length || !expression.trim()) {
			preview = null;
			return;
		}
		const timer = setTimeout(runPreview, 600);
		return () => clearTimeout(timer);
	});

	function formatValue(value: unknown): string {
		if (typeof value === 'number')
			return Number.isInteger(value) ? String(value) : value.toFixed(2);
		return value === null || value === undefined ? '—' : JSON.stringify(value);
	}

	// ---------- creating ----------

	const canCreate = $derived(
		!saving && picked.length > 0 && !!expression.trim() && !!name.trim() && !!folder
	);

	async function create(event?: Event) {
		event?.preventDefault();
		if (!canCreate) return;
		saving = true;
		errors = {};
		try {
			const res = await fetch('/fe-api/metrology/compose', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: name.trim(),
					folder,
					inputs: picked.map((p) => ({ key: p.key, instance: p.id })),
					expression,
					collection_frequency: frequency,
					unit: unit || null,
					target_value: target === '' ? null : target,
					higher_is_better: higherIsBetter
				})
			});
			const body = await res.json().catch(() => ({}));
			if (res.status === 201) {
				toastStore.trigger({
					message: body.definition?.reused
						? m.computedMetricCreatedReusing({ name: body.definition.name })
						: m.computedMetricCreated(),
					background: 'preset-filled-success-500'
				});
				modalStore.close();
				await goto(`/metric-instances/${body.id}`);
				return;
			}
			errors =
				res.status === 400 && body && typeof body === 'object'
					? body
					: { form: [m.anErrorOccurred()] };
		} catch {
			errors = { form: [m.anErrorOccurred()] };
		} finally {
			saving = false;
		}
	}

	let modalEl = $state<HTMLFormElement | null>(null);

	onMount(async () => {
		// Opened with picks (a selection, an instance page): the formula is
		// the next thing to do. Otherwise picking is.
		if (!instanceIds.length) searchInput?.focus();
		const loads: Promise<void>[] = [
			fetch('/terminologies?field_path=metric_definition.unit&is_visible=true')
				.then((res) => (res.ok ? res.json() : []))
				.then((body) => {
					const rows = Array.isArray(body) ? body : (body.results ?? []);
					units = rows.map((row: { id: string; translated_name?: string; name?: string }) => ({
						id: row.id,
						label: row.translated_name ?? row.name ?? ''
					}));
				})
				.catch(() => {})
		];
		if (instanceIds.length) {
			const params = new URLSearchParams();
			for (const id of instanceIds) params.append('instance', id);
			loads.push(
				fetch(`/fe-api/metrology/compose-candidates?${params}`)
					.then((res) => (res.ok ? res.json() : []))
					.then((rows: Candidate[]) => {
						// In the order the author selected them.
						for (const id of instanceIds) {
							const row = rows.find((r) => r.id === id);
							if (row) add(row);
						}
					})
					.catch(() => {})
			);
		}
		await Promise.all(loads);
		if (instanceIds.length) {
			// One instance to start from: the formula starts from it too.
			if (picked.length === 1 && !expression) expression = picked[0].key;
			await tick();
			const field = modalEl?.querySelector<HTMLTextAreaElement>(
				'[data-testid="compose-expression"]'
			);
			field?.focus();
			field?.setSelectionRange(field.value.length, field.value.length);
		}
	});
</script>

{#if $modalStore[0]}
	<form
		bind:this={modalEl}
		class="card bg-surface-50-950 border border-surface-300-700 shadow-xl w-[min(64rem,calc(100vw-2rem))] max-h-[92vh] overflow-y-auto p-5 flex flex-col gap-5"
		onsubmit={create}
		data-testid="compose-metric-modal"
	>
		<header class="flex items-start justify-between gap-4">
			<div class="flex flex-col gap-1">
				<h2 class="text-2xl font-bold flex items-center gap-2">
					<i class="fa-solid fa-calculator text-primary-500" aria-hidden="true"></i>
					{m.newComputedMetric()}
				</h2>
				<p class="text-sm text-surface-600-400">{m.newComputedMetricHelpText()}</p>
			</div>
			<button
				type="button"
				aria-label={m.close()}
				class="btn-icon hover:preset-tonal"
				onclick={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</header>

		<div class="grid gap-5 md:grid-cols-[minmax(0,1fr)_17rem]">
			<div class="flex flex-col gap-5 min-w-0">
				<!-- 1. The metrics the formula reads -->
				<section class="flex flex-col gap-2" aria-labelledby="compose-inputs-title">
					<h3 id="compose-inputs-title" class="text-sm font-semibold">
						<span class="badge-icon preset-filled-primary-500 size-5 text-xs mr-1">1</span>
						{m.metricsToCombine()}
					</h3>
					<div class="relative">
						<i
							class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-surface-500 text-sm"
							aria-hidden="true"
						></i>
						<input
							bind:this={searchInput}
							bind:value={query}
							type="search"
							class="input pl-9"
							placeholder={m.searchMetricInstances()}
							autocomplete="off"
							role="combobox"
							aria-expanded={resultsOpen && offered.length > 0}
							aria-controls="compose-results"
							onfocus={() => {
								resultsOpen = true;
								search();
							}}
							oninput={() => (resultsOpen = true)}
							onclick={() => (resultsOpen = true)}
							onblur={() => setTimeout(() => (resultsOpen = false), 150)}
							onkeydown={onSearchKeydown}
							data-testid="compose-search"
						/>
						{#if resultsOpen}
							<ul
								id="compose-results"
								role="listbox"
								class="absolute left-0 right-0 top-full mt-1 z-50 max-h-72 overflow-auto card bg-surface-50-950 border border-surface-200-800 shadow-lg py-1"
							>
								{#each offered as candidate, index (candidate.id)}
									<li role="option" aria-selected={index === highlighted}>
										<button
											type="button"
											class="w-full flex items-center gap-3 px-3 py-2 text-left cursor-pointer {index ===
											highlighted
												? 'bg-primary-100-900'
												: 'hover:bg-surface-100-900'}"
											onmousedown={(e) => e.preventDefault()}
											onmouseenter={() => (highlighted = index)}
											onclick={() => add(candidate)}
											data-testid="compose-candidate"
										>
											<span class="flex flex-col min-w-0">
												<span class="text-sm font-medium truncate">{candidate.name}</span>
												<span class="text-xs text-surface-600-400 truncate">
													<i class="fa-solid fa-sitemap mr-1" aria-hidden="true"></i>{candidate
														.folder.str} · {candidate.definition.name}
												</span>
											</span>
											<span class="ml-auto font-mono text-sm text-surface-700-300 shrink-0"
												>{candidate.current_value}</span
											>
										</button>
									</li>
								{:else}
									<li class="px-3 py-2 text-sm text-surface-500">{m.noMatchingMetric()}</li>
								{/each}
							</ul>
						{/if}
					</div>
					{#if picked.length}
						<ul class="flex flex-col gap-1.5" data-testid="compose-picked">
							{#each picked as pick, index (pick.id)}
								<li
									animate:flip={{ duration: 150 }}
									class="flex items-center gap-3 rounded-base border bg-surface-100-900 px-3 py-2 transition-colors {dragOver ===
										index && dragFrom !== index
										? 'border-primary-500'
										: 'border-surface-200-800'}"
									class:opacity-50={dragFrom === index}
									draggable={picked.length > 1 && renaming === null}
									ondragstart={(e) => {
										dragFrom = index;
										e.dataTransfer?.setData('text/plain', pick.id);
										if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
									}}
									ondragover={(e) => {
										if (dragFrom === null) return;
										e.preventDefault();
										dragOver = index;
									}}
									ondrop={(e) => {
										e.preventDefault();
										if (dragFrom !== null) picked = moveItem(picked, dragFrom, index);
										endDrag();
									}}
									ondragend={endDrag}
									data-testid="compose-pick"
								>
									{#if picked.length > 1}
										<button
											type="button"
											class="shrink-0 -ml-1 px-1 cursor-grab active:cursor-grabbing text-surface-400-600 hover:text-surface-900-100"
											title={`${m.dragToReorder()} (↑ ↓)`}
											aria-label={`${m.dragToReorder()}: ${pick.name}`}
											onkeydown={(e) => moveWithKeys(e, index)}
											data-handle={pick.id}
										>
											<i class="fa-solid fa-grip-vertical" aria-hidden="true"></i>
										</button>
									{/if}
									{#if renaming === index}
										<span class="flex flex-col">
											<input
												bind:this={renameInput}
												bind:value={renameValue}
												class="input input-sm font-mono text-xs w-40 py-0.5 {renameProblem
													? 'input-error'
													: ''}"
												aria-label={m.rename()}
												onblur={commitRename}
												onkeydown={(e) => {
													if (e.key === 'Enter') {
														e.preventDefault();
														commitRename();
													} else if (e.key === 'Escape') {
														e.stopPropagation();
														renaming = null;
													}
												}}
											/>
											{#if renameProblem === 'taken'}
												<span class="text-[11px] text-error-500">{m.formulaNameTaken()}</span>
											{:else if renameProblem}
												<span class="text-[11px] text-error-500">{m.datasetNameInvalid()}</span>
											{/if}
										</span>
									{:else}
										<span class="inline-flex items-stretch shrink-0">
											<button
												type="button"
												class="chip preset-outlined-primary-500 text-primary-700-300 hover:preset-filled-primary-500 cursor-pointer gap-1 px-2 py-0.5 text-xs font-mono transition-colors rounded-r-none"
												title={m.insertReference()}
												aria-label={`${m.insertReference()}: ${pick.key}`}
												onclick={() => insert(pick.key)}
												data-testid="compose-key"
											>
												<i class="fa-solid fa-plus text-[10px]" aria-hidden="true"></i>{pick.key}
											</button>
											<button
												type="button"
												class="chip preset-outlined-primary-500 text-primary-700-300 hover:preset-tonal-primary cursor-pointer px-1.5 py-0.5 text-xs rounded-l-none border-l-0"
												title={m.rename()}
												aria-label={`${m.rename()}: ${pick.key}`}
												onclick={() => startRename(index)}
											>
												<i class="fa-solid fa-pen text-[10px]" aria-hidden="true"></i>
											</button>
										</span>
									{/if}
									<span class="flex flex-col min-w-0">
										<span class="text-sm truncate">{pick.name}</span>
										<span class="text-xs text-surface-600-400 truncate">{pick.folder.str}</span>
									</span>
									<span class="ml-auto font-mono text-sm text-surface-700-300 shrink-0"
										>{pick.current_value}</span
									>
									<button
										type="button"
										class="btn-icon btn-icon-sm hover:preset-tonal-error shrink-0"
										title={m.remove()}
										aria-label={`${m.remove()}: ${pick.name}`}
										onclick={() => remove(index)}
									>
										<i class="fa-solid fa-xmark" aria-hidden="true"></i>
									</button>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-xs text-surface-500">{m.composeEmptyHint()}</p>
					{/if}
					{#each errors.inputs ?? [] as message (message)}
						<p class="text-xs text-error-500">{message}</p>
					{/each}
				</section>

				<!-- 2. The formula -->
				<section class="flex flex-col gap-2" aria-labelledby="compose-formula-title">
					<h3 id="compose-formula-title" class="text-sm font-semibold">
						<span class="badge-icon preset-filled-primary-500 size-5 text-xs mr-1">2</span>
						{m.formula()}
					</h3>
					{#if quick.length}
						<div class="flex flex-wrap items-center gap-1.5">
							<span class="text-xs text-surface-500">{m.startFrom()}</span>
							{#each quick as formula (formula.kind)}
								<button
									type="button"
									class="btn btn-sm preset-tonal-secondary text-xs py-0.5"
									title={formula.expression}
									onclick={() => (expression = formula.expression)}
									data-testid="compose-quick-{formula.kind}"
								>
									{QUICK_LABELS[formula.kind]()}
								</button>
							{/each}
						</div>
					{/if}
					<CelInput
						bind:value={expression}
						scope={celScope}
						testid="compose-expression"
						placeholder={keys.length >= 2
							? `${keys[0]} * 100.0 / ${keys[1]}`
							: keys.length
								? `${keys[0]} * 2`
								: 'clicks * 100.0 / headcount'}
					/>
					<span class="text-xs text-surface-500">{m.metricExpressionHelpText()}</span>
					{#each errors.expression ?? [] as message (message)}
						<p class="text-xs text-error-500">{message}</p>
					{/each}
				</section>
			</div>

			<!-- The live result: what the metric would hold now -->
			<aside
				class="rounded-container border border-dashed border-surface-300-700 bg-surface-100-900 p-3 flex flex-col gap-2 h-fit md:sticky md:top-0"
				aria-label={m.tryFormula()}
				data-testid="compose-preview"
			>
				<header class="flex items-center gap-2 text-sm font-semibold">
					<i class="fa-solid fa-flask text-primary-500" aria-hidden="true"></i>
					{m.latestResult()}
					{#if previewBusy}
						<i class="fa-solid fa-spinner fa-spin text-xs text-surface-500" aria-hidden="true"></i>
					{/if}
				</header>
				{#if !picked.length || !expression.trim()}
					<p class="text-xs text-surface-500">{m.composePreviewHint()}</p>
				{:else if preview?.ok}
					<div class="flex items-baseline gap-2">
						<span
							class="text-3xl font-bold text-primary-600-400 font-mono"
							data-testid="compose-value"
						>
							{formatValue(preview.value)}
						</span>
						{#if unitLabel}
							<span class="text-sm text-surface-500">{unitLabel}</span>
						{/if}
						{#if trend}
							<span
								class="badge text-xs ml-auto {trend.good === null
									? 'preset-tonal-surface'
									: trend.good
										? 'preset-tonal-success'
										: 'preset-tonal-error'}"
								title={m.changeFromPreviousPeriod()}
								data-testid="compose-trend"
							>
								<i
									class="fa-solid {trend.delta > 0
										? 'fa-arrow-trend-up'
										: trend.delta < 0
											? 'fa-arrow-trend-down'
											: 'fa-minus'}"
									aria-hidden="true"
								></i>
								{trend.delta > 0 ? '+' : ''}{formatValue(trend.delta)}
							</span>
						{/if}
					</div>
					{#if chart}
						<figure class="flex flex-col gap-1" data-testid="compose-chart">
							<svg
								viewBox="0 0 {CHART.width} {CHART.height}"
								class="w-full h-auto overflow-visible text-primary-500"
								role="img"
								aria-label={m.recentResults()}
								onmouseleave={() => (hovered = null)}
							>
								<defs>
									<linearGradient id="{chartId}-fill" x1="0" y1="0" x2="0" y2="1">
										<stop offset="0%" stop-color="currentColor" stop-opacity="0.35" />
										<stop offset="100%" stop-color="currentColor" stop-opacity="0" />
									</linearGradient>
								</defs>
								<!-- Keyed on the shape: a new formula draws its line again. -->
								{#key chart.line}
									<path d={chart.area} fill="url(#{chartId}-fill)" class="spark-area" />
									<path
										d={chart.line}
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linejoin="round"
										stroke-linecap="round"
										pathLength="1"
										class="spark-line"
									/>
								{/key}
								{#each chart.points as point, index (point.start)}
									{@const latest = index === chart.points.length - 1}
									{#if latest}
										<circle
											cx={point.x}
											cy={point.y}
											r="3.5"
											fill="currentColor"
											class="spark-pulse"
										/>
									{/if}
									<circle
										cx={point.x}
										cy={point.y}
										r={latest || hovered === point ? 3.5 : 2}
										fill="currentColor"
									/>
									<!-- A wider, invisible target than the dot itself. -->
									<circle
										cx={point.x}
										cy={point.y}
										r="9"
										fill="transparent"
										role="presentation"
										onmouseenter={() => (hovered = point)}
									/>
								{/each}
							</svg>
							<figcaption class="flex justify-between text-[10px] font-mono text-surface-500">
								{#if hovered}
									<span>{hovered.start.slice(0, 10)}</span>
									<span class="text-surface-900-100 font-semibold"
										>{formatValue(hovered.value)}</span
									>
								{:else}
									<span>{chart.points[0].start.slice(0, 10)}</span>
									<span>{chart.points[chart.points.length - 1].start.slice(0, 10)}</span>
								{/if}
							</figcaption>
						</figure>
					{/if}
					{#if recentPeriods.length}
						<table class="w-full text-xs">
							<thead>
								<tr class="text-left text-surface-500">
									<th class="font-normal">{m.previewPeriod()}</th>
									<th class="font-normal text-right">{m.previewResult()}</th>
								</tr>
							</thead>
							<tbody>
								{#each recentPeriods as period (period.start)}
									<tr>
										<td class="font-mono py-0.5">{period.start.slice(0, 10)}</td>
										<td class="font-mono text-right">
											{#if period.skipped}
												<span class="text-surface-500">{m.previewSkipped()}</span>
											{:else}
												{formatValue(period.value)}
											{/if}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{:else}
						<span class="text-xs text-surface-500">{m.previewNoPeriods()}</span>
					{/if}
				{:else if preview}
					<ul class="text-xs text-error-500 list-disc pl-4">
						{#each preview.errors ?? [] as err (err.message)}
							<li>{err.message}</li>
						{/each}
					</ul>
				{/if}
			</aside>
		</div>

		<!-- 3. What it is called and where it lives -->
		<section class="flex flex-col gap-3" aria-labelledby="compose-details-title">
			<h3 id="compose-details-title" class="text-sm font-semibold">
				<span class="badge-icon preset-filled-primary-500 size-5 text-xs mr-1">3</span>
				{m.nameAndPlace()}
			</h3>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1.5fr_1fr]">
				<label class="label flex flex-col gap-1">
					<span class="text-xs font-semibold">{m.name()} *</span>
					<input
						class="input"
						bind:value={name}
						placeholder={m.computedMetricNamePlaceholder()}
						data-testid="compose-name"
					/>
					{#each errors.name ?? [] as message (message)}
						<span class="text-xs text-error-500">{message}</span>
					{/each}
				</label>
				<label class="label flex flex-col gap-1">
					<span class="text-xs font-semibold">{m.domain()}</span>
					<select
						class="select"
						bind:value={folder}
						disabled={!domains.length}
						data-testid="compose-domain"
					>
						{#each domains as domain (domain.id)}
							<option value={domain.id}>{domain.str}</option>
						{/each}
					</select>
					{#if contextLoaded && !domains.length}
						<span class="text-xs text-error-500">{m.noDomainToCreateIn()}</span>
					{/if}
				</label>
				<label class="label flex flex-col gap-1">
					<span class="text-xs font-semibold">{m.collectionFrequency()}</span>
					<select
						class="select"
						bind:value={frequency}
						onchange={() => (frequencyChosen = true)}
						data-testid="compose-frequency"
					>
						{#each FREQUENCIES as [value, label] (value)}
							<option {value}>{label()}</option>
						{/each}
					</select>
				</label>
				<label class="label flex flex-col gap-1">
					<span class="text-xs font-semibold">{m.unit()}</span>
					<select class="select" bind:value={unit} data-testid="compose-unit">
						<option value="">—</option>
						{#each units as option (option.id)}
							<option value={option.id}>{option.label}</option>
						{/each}
					</select>
				</label>
				<label class="label flex flex-col gap-1">
					<span class="text-xs font-semibold">{m.targetValue()}</span>
					<input
						class="input"
						type="number"
						step="any"
						bind:value={target}
						data-testid="compose-target"
					/>
					{#each errors.target_value ?? [] as message (message)}
						<span class="text-xs text-error-500">{message}</span>
					{/each}
				</label>
				<label class="flex items-center gap-2 cursor-pointer self-end pb-2">
					<input type="checkbox" class="checkbox" bind:checked={higherIsBetter} />
					<span class="text-sm">{m.higherIsBetter()}</span>
				</label>
			</div>
			{#each [...(errors.folder ?? []), ...(errors.collection_frequency ?? []), ...(errors.unit ?? []), ...(errors.form ?? [])] as message (message)}
				<p class="text-xs text-error-500">{message}</p>
			{/each}
		</section>

		<footer class="flex items-center justify-end gap-2 border-t border-surface-200-800 pt-4">
			<button type="button" class="btn preset-tonal" onclick={parent.onClose}>{m.cancel()}</button>
			<button
				type="submit"
				class="btn preset-filled-primary-500"
				disabled={!canCreate}
				data-testid="compose-create"
			>
				{#if saving}
					<i class="fa-solid fa-spinner fa-spin mr-2" aria-hidden="true"></i>
				{:else}
					<i class="fa-solid fa-check mr-2" aria-hidden="true"></i>
				{/if}
				{m.createComputedMetric()}
			</button>
		</footer>
	</form>
{/if}

<style>
	/* The line draws itself in, the area fades in under it, and the latest
	   point breathes: a formula's result arriving, not a static picture. */
	.spark-line {
		stroke-dasharray: 1;
		animation: spark-draw 0.8s ease-out;
	}
	.spark-area {
		animation: spark-fade 0.8s ease-out;
	}
	.spark-pulse {
		transform-box: fill-box;
		transform-origin: center;
		animation: spark-pulse 2s ease-out infinite;
	}
	@keyframes spark-draw {
		from {
			stroke-dashoffset: 1;
		}
	}
	@keyframes spark-fade {
		from {
			opacity: 0;
		}
	}
	@keyframes spark-pulse {
		from {
			opacity: 0.6;
			transform: scale(1);
		}
		to {
			opacity: 0;
			transform: scale(3);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.spark-line,
		.spark-area,
		.spark-pulse {
			animation: none;
		}
	}
</style>
