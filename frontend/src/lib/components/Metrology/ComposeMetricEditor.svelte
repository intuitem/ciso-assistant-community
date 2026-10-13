<script lang="ts" module>
	// A computed metric started from instances: pick them, write a formula,
	// name it. The backend makes the definition (or reuses an identical one)
	// and the instance, pinned to the picks, in a domain holding them all.
	// Shown in a modal to create one, and in a drawer beside the metric to
	// edit its formula: there the name and domain stay the edit form's.
	export interface Candidate {
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
	// A computed metric as the backend hands it over for editing
	// (metric-instances/<id>/composition).
	export interface Composition {
		composable: boolean;
		definition: { id: string; name: string; shared_with: number };
		expression: string;
		name: string;
		description?: string | null;
		folder: { id: string; str: string };
		collection_frequency: string | null;
		target_value: number | null;
		category: 'quantitative' | 'qualitative';
		choices_definition: { ref_id: string | null; name: string | null }[];
		unit: string | null;
		higher_is_better: boolean;
		inputs: { key: string; instance: Candidate | null }[];
	}
	// The save's answer: the instance, and when editing what its edit form
	// holds and must adopt (compose may move it to a definition of its own).
	export interface Saved {
		id: string;
		outcome?: string;
		last_computed_at?: string | null;
		metric_definition?: string;
		input_choices?: Record<string, unknown>;
		definition?: { name: string; reused?: boolean };
	}
</script>

<script lang="ts">
	import { onMount, tick, untrack } from 'svelte';
	import { flip } from 'svelte/animate';
	import { m } from '$paraglide/messages';
	import CelInput from '$lib/components/Cel/CelInput.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import OrderedEntryList from '$lib/components/OrderedEntryList.svelte';
	import { defaults, superForm, type SuperForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { page } from '$app/state';
	import { getToastStore } from '$lib/components/Toast/stores';
	import {
		samplesOnPeriods,
		sparkRange,
		datasetNameProblem,
		formulaKey,
		formulaScope,
		keepOrFirst,
		latestTrend,
		levelIndex,
		levelStarter,
		moveItem,
		sparkline,
		quickFormulas,
		renameLiteral,
		renameReference,
		stringLiterals,
		syncLevels,
		unknownLevels,
		type Level,
		type QuickFormula,
		type SparkPoint
	} from '$lib/utils/derived-metrics';

	interface Props {
		layout?: 'modal' | 'drawer';
		// Instances to start with: a list selection, or the instance page.
		instanceIds?: string[];
		// Editing: the metric, as it is now.
		instanceId?: string;
		composition?: Composition;
		onClose: () => void;
		onSaved: (saved: Saved) => void;
	}

	let {
		layout = 'modal',
		instanceIds = [],
		instanceId,
		composition,
		onClose,
		onSaved
	}: Props = $props();
	const editing = $derived(!!instanceId && !!composition);
	const drawer = $derived(layout === 'drawer');
	// The chat launcher sits bottom-right: the drawer's buttons keep clear.
	const chatBubble = $derived(Boolean(page.data?.featureflags?.chat_mode));

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
	// The domain follows the picks (the lowest holding them all) until the
	// author chooses one; then it stays while it is still offered.
	let folderChosen = false;
	// The usual domain picker needs a form to bind to: a client-side one, its
	// value mirrored into `folder`. Not named "folder", or the picker would
	// offer the personal space, where the picks can never be.
	// It also backs the "use the levels of" definition picker.
	const domainSchema = z.object({
		target_folder: z.string(),
		levels_from: z.string().nullable().optional()
	});
	const domainForm = superForm(
		defaults({ target_folder: '', levels_from: null }, zod(domainSchema)),
		{
			dataType: 'json',
			taintedMessage: false,
			validators: zod(domainSchema),
			SPA: true
		}
	);
	// AutocompleteSelect types its form loosely; the same form, as it expects it.
	const levelsForm = domainForm as unknown as SuperForm<Record<string, unknown>, any>;
	let units = $state<{ id: string; label: string }[]>([]);
	let unit = $state('');
	let target = $state('');
	let higherIsBetter = $state(true);

	// The result: a number, or one of an ordered list of levels (a qualitative
	// metric). The levels follow the texts the formula returns until the
	// author takes them from an existing definition.
	let resultKind = $state<'number' | 'level'>('number');
	const isLevel = $derived(resultKind === 'level');
	let levels = $state<Level[]>([]);
	let levelsFrom = $state<string | null>(null);
	// The levels as they were before the editor's last change: tells a
	// rename, which the formula follows, from a reorder.
	let previousLevels: Level[] = [];

	function setLevels(next: Level[]) {
		levels = next;
		previousLevels = next;
	}

	$effect(() => {
		if (!isLevel || levelsFrom) return;
		const texts = stringLiterals(expression);
		const timer = setTimeout(() => {
			const current = untrack(() => levels);
			const next = syncLevels(current, texts);
			if (next !== current) setLevels(next);
		}, 300);
		return () => clearTimeout(timer);
	});

	function onLevelsChange(next: Level[]) {
		let renamed = expression;
		for (const level of next) {
			const before =
				previousLevels.find((p) => p.ref_id === level.ref_id) ??
				previousLevels.find((p) => p.name === level.name);
			if (!before) continue;
			renamed = renameLiteral(renamed, before.name, level.name);
			renamed = renameLiteral(renamed, before.ref_id, level.ref_id);
		}
		expression = renamed;
		setLevels(next);
	}

	async function useLevelsOf(id: unknown) {
		if (typeof id !== 'string' || !id) {
			levelsFrom = null;
			return;
		}
		try {
			const res = await fetch(`/fe-api/metrology/metric-definitions/${id}`);
			if (!res.ok) return;
			const body = await res.json();
			const choices: { ref_id?: unknown; name?: unknown }[] = Array.isArray(body.choices_definition)
				? body.choices_definition
				: [];
			// A level without a reference (older or imported definitions) gets
			// one from its name: the new definition needs both.
			const taken: string[] = [];
			setLevels(
				choices.map((choice) => {
					const name = String(choice.name ?? '');
					const ref_id = String(choice.ref_id ?? '').trim() || formulaKey(name, taken);
					taken.push(ref_id.toLowerCase(), name.toLowerCase());
					return { ref_id, name };
				})
			);
			levelsFrom = typeof body.name === 'string' ? body.name : id;
		} catch {
			// The picker stays as it was; the author can pick again.
		}
	}

	const unknownTexts = $derived(isLevel ? unknownLevels(expression, levels) : []);
	const levelPayload = $derived(levels.map(({ ref_id, name }) => ({ ref_id, name })));

	let errors = $state<Record<string, string[]>>({});
	// Editing: inputs whose instance is gone.
	let missingInputs = $state<string[]>([]);
	let initialDefinition = $state<string | null>(null);
	let saving = $state(false);
	let contextLoaded = $state(false);

	// ---------- picking ----------

	let searchInput = $state<HTMLInputElement | null>(null);
	let query = $state('');
	let results = $state<Candidate[]>([]);
	let resultsOpen = $state(false);
	let highlighted = $state(0);
	let searchSeq = 0;
	// Picked instances stay in the results, checked: the list shows what is
	// picked while it covers the picked rows below it.
	const pickedIds = $derived(new Set(picked.map((p) => p.id)));

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

	// A result picks, or unpicks when already picked.
	function toggle(candidate: Candidate) {
		const index = picked.findIndex((p) => p.id === candidate.id);
		if (index === -1) add(candidate);
		else remove(index);
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
		rootEl?.querySelector<HTMLButtonElement>(`[data-handle="${id}"]`)?.focus();
	}

	function onSearchKeydown(event: KeyboardEvent) {
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			resultsOpen = true;
			highlighted = Math.min(highlighted + 1, results.length - 1);
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			highlighted = Math.max(highlighted - 1, 0);
		} else if (event.key === 'Enter') {
			event.preventDefault();
			if (resultsQuery === query.trim()) {
				if (results[highlighted]) toggle(results[highlighted]);
				return;
			}
			// Typed faster than the search answered: answer it now and add the
			// best match not picked yet (never unpick on a blind Enter).
			resultsOpen = true;
			search().then(() => {
				const best = results.find((r) => !pickedIds.has(r.id));
				if (resultsQuery === query.trim() && best) add(best);
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
	const quick = $derived(expression.trim() || isLevel ? [] : quickFormulas(keys));
	const starter = $derived(isLevel && !expression.trim() ? levelStarter(keys) : '');
	const inputs = $derived(
		picked.map((p) => ({ key: p.key, definition: p.definition.id, combine: 'one' as const }))
	);
	const choices = $derived(Object.fromEntries(picked.map((p) => [p.key, { pick: p.id }])));

	// What the definition holds (mirrors compose._same_formula): an edit that
	// changes it may reach other metrics, and recomputes the past.
	const definitionState = $derived(
		JSON.stringify([
			inputs.map((input) => `${input.key}:${input.definition}`).sort(),
			expression.trim(),
			isLevel,
			isLevel ? levelPayload : [],
			isLevel ? null : unit || null,
			higherIsBetter
		])
	);
	const definitionChanged = $derived(
		editing && initialDefinition !== null && definitionState !== initialDefinition
	);
	const sharedWith = $derived(composition?.definition.shared_with ?? 0);
	// Anything to save: the definition, or the instance's own picks and
	// settings (a pick swapped for another of the same definition).
	const editState = $derived(
		JSON.stringify([
			definitionState,
			picked.map((p) => `${p.key}:${p.id}`),
			name.trim(),
			folder,
			frequency,
			target
		])
	);
	let initialEdit = $state<string | null>(null);
	const edited = $derived(editing && initialEdit !== null && editState !== initialEdit);

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
				// The drawer edits the formula only: the domain is the edit
				// form's, and a pick it cannot hold is said, not worked around.
				if (!drawer) {
					folder = folderChosen ? keepOrFirst(folder, domains) : (domains[0]?.id ?? '');
					domainForm.form.update((data) => ({ ...data, target_folder: folder }));
				}
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

	// The last year or so of periods, as a small chart under the value; the
	// drawer has the room for two years, and the metric as it is now beside.
	const CHART = $derived(
		drawer ? { width: 480, height: 120, periods: 24 } : { width: 240, height: 64, periods: 12 }
	);
	const chartId = $props.id();
	// A level plots at its position in the list.
	const chartPeriods = $derived(
		(preview?.periods ?? [])
			.slice(-CHART.periods)
			.map((period) => (isLevel ? { ...period, value: levelIndex(period.value, levels) } : period))
	);

	// Editing: the metric's own samples, the "now" line the new one is read
	// against. A level is placed in the levels being edited, by its name.
	let samples = $state<{ timestamp: string; period_start?: string | null; value: unknown }[]>([]);
	const nowPeriods = $derived.by(() => {
		if (!editing || !samples.length || !chartPeriods.length) return [];
		if ((composition?.category === 'qualitative') !== isLevel) return [];
		const names = composition?.choices_definition ?? [];
		return samplesOnPeriods(chartPeriods, samples, (value) =>
			isLevel
				? levelIndex(names[Number(value.choice_index) - 1]?.name ?? null, levels)
				: value.result
		);
	});
	const chartRange = $derived(sparkRange(chartPeriods, nowPeriods));
	const chart = $derived(sparkline(chartPeriods, CHART.width, CHART.height, 6, chartRange));
	const nowChart = $derived(sparkline(nowPeriods, CHART.width, CHART.height, 6, chartRange));
	const nowAt = $derived(new Map(nowPeriods.map((period) => [period.start, period])));
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
					category: isLevel ? 'qualitative' : 'quantitative',
					choices_definition: isLevel ? levelPayload : undefined
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
	const previewKey = $derived(
		JSON.stringify([folder, frequency, inputs, choices, expression, isLevel, levelPayload])
	);
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
		if (typeof value === 'string') return value;
		return value === null || value === undefined ? '—' : JSON.stringify(value);
	}

	// A charted level is its position: show its name.
	function formatPoint(value: number): string {
		return isLevel ? (levels[value - 1]?.name ?? formatValue(value)) : formatValue(value);
	}

	// ---------- creating ----------

	// The drawer never moves the metric: a domain that cannot hold a pick
	// is said before the save refuses it.
	const outsideDomain = $derived(
		drawer && contextLoaded && !!folder && !domains.some((domain) => domain.id === folder)
	);
	const canCreate = $derived(
		!saving &&
			picked.length > 0 &&
			!!expression.trim() &&
			!!name.trim() &&
			!!folder &&
			!outsideDomain &&
			(!editing || edited)
	);

	async function create(event?: Event) {
		event?.preventDefault();
		if (!canCreate) return;
		saving = true;
		errors = {};
		try {
			const res = await fetch(
				editing ? `/fe-api/metrology/composition/${instanceId}` : '/fe-api/metrology/compose',
				{
					method: editing ? 'PUT' : 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						name: name.trim(),
						folder,
						inputs: picked.map((p) => ({ key: p.key, instance: p.id })),
						expression,
						collection_frequency: frequency,
						category: isLevel ? 'qualitative' : 'quantitative',
						choices_definition: isLevel ? levelPayload : undefined,
						unit: isLevel ? null : unit || null,
						target_value: isLevel || target === '' ? null : target,
						higher_is_better: higherIsBetter
					})
				}
			);
			const body = await res.json().catch(() => ({}));
			if (editing && res.ok) {
				toastStore.trigger({
					message:
						body.outcome === 'forked' ? m.computedMetricSavedForked() : m.computedMetricSaved(),
					background: 'preset-filled-success-500'
				});
				onSaved(body);
				return;
			}
			if (res.status === 201) {
				toastStore.trigger({
					message: body.definition?.reused
						? m.computedMetricCreatedReusing({ name: body.definition.name })
						: m.computedMetricCreated(),
					background: 'preset-filled-success-500'
				});
				onSaved(body);
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

	let rootEl = $state<HTMLFormElement | null>(null);

	// Enter submits the modal from its own fields (name, target). In a field
	// that belongs to a widget (adding a level, searching a picker) Enter is
	// the widget's: the browser would otherwise submit the form with it.
	// Cmd or Ctrl+Enter saves from anywhere, the formula field included.
	function keepEnterInWidgets(event: KeyboardEvent) {
		if (event.key !== 'Enter') return;
		if (event.metaKey || event.ctrlKey) {
			event.preventDefault();
			create();
			return;
		}
		const target = event.target as HTMLElement | null;
		if (target?.tagName !== 'INPUT') return;
		if (target.closest('[data-testid="compose-levels"], [data-testid="compose-domain"]')) {
			event.preventDefault();
		}
	}

	// Closing the drawer on an edit not saved asks first: it sits beside the
	// page, one stray Escape away from losing a formula.
	let confirmingClose = $state(false);
	function requestClose() {
		if (edited && !confirmingClose) {
			confirmingClose = true;
			return;
		}
		onClose();
	}
	function onWindowKeydown(event: KeyboardEvent) {
		// A list or picker inside closes itself first (it stops the event).
		if (!drawer || event.key !== 'Escape' || event.defaultPrevented) return;
		if (confirmingClose) confirmingClose = false;
		else requestClose();
	}

	onMount(async () => {
		if (editing && instanceId) {
			const params = new URLSearchParams({ metric_instance: instanceId, limit: '200' });
			fetch(`/custom-metric-samples?${params}`)
				.then((res) => (res.ok ? res.json() : []))
				.then((body) => {
					samples = Array.isArray(body) ? body : (body?.results ?? []);
				})
				.catch(() => {});
		}
		if (composition) {
			const c = composition;
			picked = c.inputs
				.filter((input) => input.instance)
				.map((input) => ({ ...(input.instance as Candidate), key: input.key }));
			missingInputs = c.inputs.filter((input) => !input.instance).map((input) => input.key);
			expression = c.expression;
			resultKind = c.category === 'qualitative' ? 'level' : 'number';
			setLevels(
				(c.choices_definition ?? []).map((choice) => ({
					ref_id: choice.ref_id ?? '',
					name: choice.name ?? ''
				}))
			);
			name = c.name;
			folder = c.folder.id;
			folderChosen = true;
			domainForm.form.update((data) => ({ ...data, target_folder: folder }));
			frequency = c.collection_frequency ?? 'monthly';
			frequencyChosen = true;
			unit = c.unit ?? '';
			target =
				c.target_value === null || c.target_value === undefined ? '' : String(c.target_value);
			higherIsBetter = c.higher_is_better;
			await tick();
			initialDefinition = definitionState;
			initialEdit = editState;
			if (drawer) focusFormula();
		}
		// Opened with picks (a selection, an instance page): the formula is
		// the next thing to do. Otherwise picking is.
		else if (!instanceIds.length) searchInput?.focus();
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
			focusFormula();
		}
	});

	function focusFormula() {
		const field = rootEl?.querySelector<HTMLTextAreaElement>('[data-testid="compose-expression"]');
		field?.focus();
		field?.setSelectionRange(field.value.length, field.value.length);
	}
</script>

<svelte:window onkeydown={onWindowKeydown} />

<form
	bind:this={rootEl}
	class={drawer
		? 'flex flex-col h-full min-h-0'
		: 'card bg-surface-50-950 border border-surface-300-700 shadow-xl w-[min(64rem,calc(100vw-2rem))] max-h-[92vh] overflow-y-auto p-5 flex flex-col gap-5'}
	onsubmit={create}
	onkeydown={keepEnterInWidgets}
	data-testid="compose-metric-{layout}"
>
	<header
		class="flex items-start justify-between gap-4 {drawer
			? 'p-4 border-b border-surface-200-800'
			: ''}"
	>
		<div class="flex flex-col gap-1">
			<h2
				id="{chartId}-title"
				class="{drawer ? 'text-lg' : 'text-2xl'} font-bold flex items-center gap-2"
			>
				<i class="fa-solid fa-calculator text-primary-500" aria-hidden="true"></i>
				{editing ? m.editComputedMetric() : m.newComputedMetric()}
			</h2>
			<p class="text-sm text-surface-600-400">
				{editing ? m.editComputedMetricHelpText() : m.newComputedMetricHelpText()}
			</p>
		</div>
		<button
			type="button"
			aria-label={m.close()}
			class="btn-icon hover:preset-tonal"
			onclick={drawer ? requestClose : onClose}
		>
			<i class="fa-solid fa-xmark"></i>
		</button>
	</header>

	<!-- The drawer scrolls its body between a fixed header and footer. -->
	<div class={drawer ? 'flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-5' : 'contents'}>
		<div class={drawer ? 'flex flex-col gap-5' : 'grid gap-5 md:grid-cols-[minmax(0,1fr)_17rem]'}>
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
							aria-expanded={resultsOpen && results.length > 0}
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
								aria-multiselectable="true"
								class="absolute left-0 right-0 top-full mt-1 z-50 max-h-72 overflow-auto card bg-surface-50-950 border border-surface-200-800 shadow-lg py-1"
							>
								{#if picked.length}
									<!-- The picks this list covers, summed up where the eye is. -->
									<li
										class="sticky top-0 z-10 bg-surface-100-900 border-b border-surface-200-800 px-3 py-1.5 text-xs text-surface-700-300 truncate"
										role="presentation"
										title={picked.map((p) => p.name).join(', ')}
										data-testid="compose-picked-summary"
									>
										<i class="fa-solid fa-list-check text-primary-500 mr-1" aria-hidden="true"></i>
										{m.pickedSummary({
											count: picked.length,
											names: picked.map((p) => p.name).join(', ')
										})}
									</li>
								{/if}
								{#each results as candidate, index (candidate.id)}
									{@const isPicked = pickedIds.has(candidate.id)}
									<li role="option" aria-selected={isPicked}>
										<button
											type="button"
											class="w-full flex items-center gap-3 px-3 py-2 text-left cursor-pointer {index ===
											highlighted
												? 'bg-primary-100-900'
												: isPicked
													? 'bg-primary-50-950 hover:bg-surface-100-900'
													: 'hover:bg-surface-100-900'}"
											onmousedown={(e) => e.preventDefault()}
											onmouseenter={() => (highlighted = index)}
											onclick={() => toggle(candidate)}
											title={isPicked ? m.remove() : undefined}
											data-testid="compose-candidate"
										>
											<i
												class="{isPicked
													? 'fa-solid fa-square-check text-primary-500'
													: 'fa-regular fa-square text-surface-400-600'} shrink-0"
												aria-hidden="true"
											></i>
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
									class="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-base border bg-surface-100-900 px-3 py-2 transition-colors {dragOver ===
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
									<!-- Wraps under a long formula name rather than shrink to nothing. -->
									<span class="flex flex-col min-w-[8rem] flex-1">
										<span class="text-sm truncate" title={pick.name}>{pick.name}</span>
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
					{#if outsideDomain}
						<p class="text-xs text-warning-600-400" data-testid="compose-outside-domain">
							<i class="fa-solid fa-triangle-exclamation mr-1" aria-hidden="true"
							></i>{m.pickOutsideDomain({ domain: composition?.folder.str ?? '' })}
						</p>
					{/if}
					{#if missingInputs.length}
						<p class="text-xs text-warning-600-400" data-testid="compose-missing-inputs">
							<i class="fa-solid fa-triangle-exclamation mr-1" aria-hidden="true"
							></i>{m.inputsToPickAgain({ keys: missingInputs.join(', ') })}
						</p>
					{/if}
					{#each errors.inputs ?? [] as message (message)}
						<p class="text-xs text-error-500">{message}</p>
					{/each}
				</section>

				<!-- 2. The formula -->
				<section class="flex flex-col gap-2" aria-labelledby="compose-formula-title">
					<div class="flex items-center justify-between gap-2 flex-wrap">
						<h3 id="compose-formula-title" class="text-sm font-semibold">
							<span class="badge-icon preset-filled-primary-500 size-5 text-xs mr-1">2</span>
							{m.formula()}
						</h3>
						<div
							class="flex items-center gap-1 text-xs"
							role="radiogroup"
							aria-label={m.resultType()}
							data-testid="compose-result-kind"
						>
							<span class="text-surface-500 mr-1">{m.resultType()}</span>
							{#each [['number', m.resultNumber()], ['level', m.resultLevel()]] as [kind, label] (kind)}
								<button
									type="button"
									role="radio"
									aria-checked={resultKind === kind}
									class="btn btn-sm text-xs py-0.5 {resultKind === kind
										? 'preset-filled-primary-500'
										: 'preset-tonal'}"
									onclick={() => (resultKind = kind as 'number' | 'level')}
									data-testid="compose-result-{kind}"
								>
									<i
										class="fa-solid {kind === 'number' ? 'fa-hashtag' : 'fa-list-ol'} mr-1"
										aria-hidden="true"
									></i>{label}
								</button>
							{/each}
						</div>
					</div>
					{#if starter}
						<div class="flex flex-wrap items-center gap-1.5">
							<span class="text-xs text-surface-500">{m.startFrom()}</span>
							<button
								type="button"
								class="btn btn-sm preset-tonal-secondary text-xs py-0.5"
								title={starter}
								onclick={() => (expression = starter)}
								data-testid="compose-quick-threshold">{m.quickFormulaThreshold()}</button
							>
						</div>
					{/if}
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
						placeholder={isLevel
							? levelStarter(keys) || 'rate >= 50.0 ? "High" : "Low"'
							: keys.length >= 2
								? `${keys[0]} * 100.0 / ${keys[1]}`
								: keys.length
									? `${keys[0]} * 2`
									: 'clicks * 100.0 / headcount'}
					/>
					<span class="text-xs text-surface-500">{m.metricExpressionHelpText()}</span>
					{#each errors.expression ?? [] as message (message)}
						<p class="text-xs text-error-500">{message}</p>
					{/each}
					{#if isLevel}
						<!-- The levels, as the definition form shows them: edit, add, reorder. -->
						<div
							class="flex flex-col gap-2 rounded-base border border-surface-200-800 p-3"
							data-testid="compose-levels"
						>
							<div class="flex items-center justify-between gap-2 flex-wrap">
								<span class="text-sm font-semibold">{m.levels()}</span>
								<div class="w-72">
									<AutocompleteSelect
										form={levelsForm}
										field="levels_from"
										optionsEndpoint="metric-definitions"
										optionsDetailedUrlParameters={[['category', 'qualitative']]}
										placeholder={m.useLevelsOf()}
										nullable
										portalDropdown
										onChange={useLevelsOf}
									/>
								</div>
							</div>
							<p class="text-xs text-surface-500">
								{levelsFrom ? m.levelsCopiedHelpText({ name: levelsFrom }) : m.levelsHelpText()}
							</p>
							<OrderedEntryList bind:entries={levels} onchange={onLevelsChange} />
							{#each unknownTexts as text (text)}
								<p class="text-xs text-warning-600-400" data-testid="compose-unknown-level">
									<i class="fa-solid fa-triangle-exclamation mr-1" aria-hidden="true"
									></i>{m.notALevel({ text })}
								</p>
							{/each}
							{#each errors.choices_definition ?? [] as message (message)}
								<p class="text-xs text-error-500">{message}</p>
							{/each}
						</div>
					{/if}
				</section>
			</div>

			<!-- The live result: what the metric would hold now -->
			<aside
				class="rounded-container border border-dashed border-surface-300-700 bg-surface-100-900 p-3 flex flex-col gap-2 h-fit {drawer
					? ''
					: 'md:sticky md:top-0'}"
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
								{#if !isLevel}{trend.delta > 0 ? '+' : ''}{formatValue(trend.delta)}{/if}
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
								{#if nowChart}
									<!-- The metric as it is now, under the line the edit would give. -->
									<path
										d={nowChart.line}
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										stroke-dasharray="4 3"
										stroke-linejoin="round"
										class="text-surface-500"
										data-testid="compose-chart-now"
									/>
								{/if}
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
									{@const now = nowAt.get(hovered.start)}
									<span>{hovered.start.slice(0, 10)}</span>
									<span class="flex gap-2">
										{#if now && !now.skipped && typeof now.value === 'number'}
											<span>{m.formulaNow()} {formatPoint(now.value)}</span>
										{/if}
										<span class="text-surface-900-100 font-semibold"
											>{formatPoint(hovered.value)}</span
										>
									</span>
								{:else}
									<span>{chart.points[0].start.slice(0, 10)}</span>
									<span>{chart.points[chart.points.length - 1].start.slice(0, 10)}</span>
								{/if}
							</figcaption>
							{#if nowChart}
								<div
									class="flex items-center gap-4 text-[11px] text-surface-600-400"
									data-testid="compose-chart-legend"
								>
									<span class="flex items-center gap-1.5">
										<svg width="18" height="4" aria-hidden="true" class="text-surface-500">
											<line
												x1="0"
												y1="2"
												x2="18"
												y2="2"
												stroke="currentColor"
												stroke-width="1.5"
												stroke-dasharray="4 3"
											/>
										</svg>{m.formulaNow()}
									</span>
									<span class="flex items-center gap-1.5">
										<svg width="18" height="4" aria-hidden="true" class="text-primary-500">
											<line x1="0" y1="2" x2="18" y2="2" stroke="currentColor" stroke-width="2" />
										</svg>{m.formulaNew()}
									</span>
								</div>
							{/if}
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
				{drawer ? m.howToReadIt() : m.nameAndPlace()}
			</h3>
			<div class="grid gap-3 sm:grid-cols-2 {drawer ? '' : 'lg:grid-cols-[2fr_1.5fr_1fr]'}">
				<!-- Name, domain and schedule are the edit form's in the drawer. -->
				{#if !drawer}
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
					<!-- Not a <label>: it would forward clicks to the picker's first button. -->
					<div class="flex flex-col gap-1" data-testid="compose-domain">
						<span class="text-xs font-semibold">{m.domain()}</span>
						<FolderTreeSelect
							form={domainForm}
							field="target_folder"
							writePermission={null}
							allowedIds={domains.map((domain) => domain.id)}
							disabled={!domains.length}
							onChange={(value: unknown) => {
								folder = typeof value === 'string' ? value : '';
								folderChosen = true;
							}}
						/>
						{#if contextLoaded && !domains.length}
							<span class="text-xs text-error-500">{m.noDomainToCreateIn()}</span>
						{/if}
					</div>
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
				{/if}
				{#if !isLevel}
					<label class="label flex flex-col gap-1">
						<span class="text-xs font-semibold">{m.unit()}</span>
						<select class="select" bind:value={unit} data-testid="compose-unit">
							<option value="">—</option>
							{#each units as option (option.id)}
								<option value={option.id}>{option.label}</option>
							{/each}
						</select>
					</label>
					{#if !drawer}
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
					{/if}
				{/if}
				<label class="flex items-center gap-2 cursor-pointer self-end pb-2">
					<input type="checkbox" class="checkbox" bind:checked={higherIsBetter} />
					<span class="text-sm">{m.higherIsBetter()}</span>
				</label>
			</div>
			{#each [...(errors.folder ?? []), ...(errors.collection_frequency ?? []), ...(errors.unit ?? []), ...(errors.category ?? []), ...(errors.form ?? [])] as message (message)}
				<p class="text-xs text-error-500">{message}</p>
			{/each}
		</section>
	</div>

	{#if definitionChanged}
		<!-- An edit of the formula reaches the past, and maybe other metrics:
			     said next to the button that does it. -->
		<div
			class="rounded-base border border-warning-500 bg-warning-50-950 p-3 text-sm flex flex-col gap-2 {drawer
				? 'mx-4 mb-3'
				: ''}"
			data-testid="compose-definition-scope"
		>
			<p>
				<i class="fa-solid fa-clock-rotate-left mr-1" aria-hidden="true"
				></i>{m.formulaChangeRecomputes()}
			</p>
			{#if sharedWith > 0}
				<!-- A shared definition is never edited from one of its metrics. -->
				<p>{m.definitionSharedFork({ count: sharedWith })}</p>
			{/if}
		</div>
	{/if}
	<footer
		class="flex items-center justify-end gap-2 border-t border-surface-200-800 {drawer
			? `p-3 ${chatBubble ? 'pr-20' : ''}`
			: 'pt-4'}"
	>
		{#if confirmingClose}
			<span class="text-sm font-semibold mr-auto" role="status">{m.unsavedChanges()}</span>
			<button type="button" class="btn preset-tonal" onclick={() => (confirmingClose = false)}
				>{m.keepEditing()}</button
			>
			<button
				type="button"
				class="btn preset-filled-error-500"
				onclick={onClose}
				data-testid="compose-discard">{m.discardChanges()}</button
			>
		{:else}
			<button type="button" class="btn preset-tonal" onclick={drawer ? requestClose : onClose}
				>{m.cancel()}</button
			>
			<button
				type="submit"
				class="btn preset-filled-primary-500"
				disabled={!canCreate}
				aria-keyshortcuts="Control+Enter Meta+Enter"
				data-testid="compose-create"
			>
				{#if saving}
					<i class="fa-solid fa-spinner fa-spin mr-2" aria-hidden="true"></i>
				{:else}
					<i class="fa-solid fa-check mr-2" aria-hidden="true"></i>
				{/if}
				{editing ? m.save() : m.createComputedMetric()}
			</button>
		{/if}
	</footer>
</form>

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
