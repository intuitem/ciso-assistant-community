<script lang="ts">
	import { m } from '$paraglide/messages';

	type Entry = { param: string; value: string };

	interface Props {
		field: string;
		label?: string;
		filterValue?: Entry[];
		// Base query param, when it differs from the filter key.
		param?: string;
		// DateTimeField columns need the `__date` transform, or `lte` drops the last day.
		isDateTime?: boolean;
		onChange?: (value: Entry[]) => void;
		[key: string]: any;
	}

	let {
		field,
		label = field,
		filterValue = [],
		param = field,
		isDateTime = false,
		onChange = () => {}
	}: Props = $props();

	const base = isDateTime ? `${param}__date` : param;
	const P = {
		gte: `${base}__gte`,
		lte: `${base}__lte`,
		gt: `${base}__gt`,
		lt: `${base}__lt`,
		isnull: `${param}__isnull`
	};

	const at = (p: string) => filterValue?.find((v) => v.param === p)?.value ?? '';

	// A preset resolves to concrete dates when picked, so a reloaded URL reads back as the
	// equivalent absolute operator rather than the preset name.
	function initialOperator() {
		if (at(P.isnull) === 'true') return 'unset';
		if (at(P.lt)) return 'before';
		if (at(P.gt)) return 'after';
		const from = at(P.gte);
		const to = at(P.lte);
		if (from && to) return from === to ? 'on' : 'between';
		if (to) return 'onOrBefore';
		if (from) return 'onOrAfter';
		return 'any';
	}

	let op = $state(initialOperator());
	let from = $state(at(P.gte) || at(P.gt));
	let to = $state(at(P.lte) || at(P.lt));

	const iso = (d: Date) =>
		`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	const shift = (days: number) => {
		const d = new Date();
		d.setDate(d.getDate() + days);
		return iso(d);
	};
	const dayOf = (y: number, mo: number, da: number) => iso(new Date(y, mo, da));

	// Each preset returns the [from, to] pair it stands for; an empty bound is open-ended.
	function presetRange(key: string): [string, string] {
		const now = new Date();
		const [y, mo] = [now.getFullYear(), now.getMonth()];
		switch (key) {
			case 'today':
				return [iso(now), iso(now)];
			case 'thisWeek': {
				const offset = (now.getDay() + 6) % 7; // weeks start Monday
				return [shift(-offset), shift(6 - offset)];
			}
			case 'thisMonth':
				return [dayOf(y, mo, 1), dayOf(y, mo + 1, 0)];
			case 'thisQuarter': {
				const q = Math.floor(mo / 3) * 3;
				return [dayOf(y, q, 1), dayOf(y, q + 3, 0)];
			}
			case 'thisYear':
				return [dayOf(y, 0, 1), dayOf(y, 11, 31)];
			case 'last7Days':
				return [shift(-6), iso(now)];
			case 'last30Days':
				return [shift(-29), iso(now)];
			case 'lastMonth':
				return [dayOf(y, mo - 1, 1), dayOf(y, mo, 0)];
			case 'lastYear':
				return [dayOf(y - 1, 0, 1), dayOf(y - 1, 11, 31)];
			case 'overdue':
				return ['', shift(-1)];
			case 'next7Days':
				return [iso(now), shift(7)];
			case 'next30Days':
				return [iso(now), shift(30)];
			case 'next90Days':
				return [iso(now), shift(90)];
			default:
				return ['', ''];
		}
	}

	const PRESETS = [
		{ value: 'today', label: m.dateToday() },
		{ value: 'thisWeek', label: m.dateThisWeek() },
		{ value: 'thisMonth', label: m.dateThisMonth() },
		{ value: 'thisQuarter', label: m.dateThisQuarter() },
		{ value: 'thisYear', label: m.dateThisYear() },
		{ value: 'last7Days', label: m.dateLast7Days() },
		{ value: 'last30Days', label: m.dateLast30Days() },
		{ value: 'lastMonth', label: m.dateLastMonth() },
		{ value: 'lastYear', label: m.dateLastYear() },
		{ value: 'overdue', label: m.overdue() },
		{ value: 'next7Days', label: m.dateNext7Days() },
		{ value: 'next30Days', label: m.dateNext30Days() },
		{ value: 'next90Days', label: m.dateNext90Days() }
	];

	const OPERATORS = [
		{ value: 'on', label: m.dateOn() },
		{ value: 'before', label: m.dateBefore() },
		{ value: 'after', label: m.dateAfter() },
		{ value: 'onOrBefore', label: m.onOrBefore() },
		{ value: 'onOrAfter', label: m.onOrAfter() },
		{ value: 'between', label: m.between() }
	];

	const PRESET_KEYS = new Set(PRESETS.map((p) => p.value));
	const needsFrom = $derived(['after', 'onOrAfter', 'on', 'between'].includes(op));
	const needsTo = $derived(['before', 'onOrBefore', 'between'].includes(op));

	function emit() {
		const entries: Entry[] = [];
		if (op === 'unset') {
			entries.push({ param: P.isnull, value: 'true' });
		} else if (PRESET_KEYS.has(op)) {
			const [lo, hi] = presetRange(op);
			if (lo) entries.push({ param: P.gte, value: lo });
			if (hi) entries.push({ param: P.lte, value: hi });
		} else if (op === 'on') {
			if (from) entries.push({ param: P.gte, value: from }, { param: P.lte, value: from });
		} else {
			if (needsFrom && from) entries.push({ param: op === 'after' ? P.gt : P.gte, value: from });
			if (needsTo && to) entries.push({ param: op === 'before' ? P.lt : P.lte, value: to });
		}
		onChange(entries);
	}

	function selectOperator(value: string) {
		op = value;
		if (!needsFrom) from = '';
		if (!needsTo) to = '';
		emit();
	}
</script>

<!-- py-1 keeps these single-row filters from reading as a dense block next to the taller
	 label-above-input ones; the fixed select width lines every operator up. -->
<div class="flex flex-col space-y-2 py-1">
	<div class="flex flex-wrap items-center justify-between gap-2">
		<span class="min-w-0 flex-1 text-sm font-semibold" id="{field}-date-filter">{label}</span>
		<select
			class="select w-36 shrink-0 text-sm"
			aria-labelledby="{field}-date-filter"
			value={op}
			onchange={(e) => selectOperator(e.currentTarget.value)}
		>
			<option value="any">{m.anyDate()}</option>
			<optgroup label={m.dateQuickRanges()}>
				{#each PRESETS as preset}
					<option value={preset.value}>{preset.label}</option>
				{/each}
			</optgroup>
			<optgroup label={m.dateSpecificDates()}>
				{#each OPERATORS as operator}
					<option value={operator.value}>{operator.label}</option>
				{/each}
			</optgroup>
			<option value="unset">{m.dateNotSet()}</option>
		</select>
	</div>
	{#if needsFrom || needsTo}
		<div class="flex items-center gap-2">
			{#if needsFrom}
				<input
					type="date"
					class="input min-w-0 flex-1 text-sm"
					aria-label="{label} - {m.onOrAfter()}"
					bind:value={from}
					onchange={emit}
				/>
			{/if}
			{#if needsFrom && needsTo}
				<i class="fa-solid fa-arrow-right text-xs text-surface-500"></i>
			{/if}
			{#if needsTo}
				<input
					type="date"
					class="input min-w-0 flex-1 text-sm"
					aria-label="{label} - {m.onOrBefore()}"
					bind:value={to}
					onchange={emit}
				/>
			{/if}
		</div>
	{/if}
</div>
