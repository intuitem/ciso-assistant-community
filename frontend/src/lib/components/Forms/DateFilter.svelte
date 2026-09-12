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
	const GTE = `${base}__gte`;
	const LTE = `${base}__lte`;
	const ISNULL = `${param}__isnull`;

	const at = (p: string) => filterValue?.find((v) => v.param === p)?.value ?? '';

	let op = $state(
		at(ISNULL) === 'true'
			? 'unset'
			: at(GTE) && at(LTE)
				? 'between'
				: at(LTE)
					? 'before'
					: at(GTE)
						? 'after'
						: 'any'
	);
	let from = $state(at(GTE));
	let to = $state(at(LTE));

	const OPERATORS = [
		{ value: 'any', label: m.anyDate() },
		{ value: 'before', label: m.onOrBefore() },
		{ value: 'after', label: m.onOrAfter() },
		{ value: 'between', label: m.between() },
		{ value: 'unset', label: m.dateNotSet() }
	];

	function emit() {
		const entries: Entry[] = [];
		if (op === 'unset') {
			entries.push({ param: ISNULL, value: 'true' });
		} else {
			if (op !== 'before' && from) entries.push({ param: GTE, value: from });
			if (op !== 'after' && to) entries.push({ param: LTE, value: to });
		}
		onChange(entries);
	}

	function selectOperator(value: string) {
		op = value;
		if (op === 'any' || op === 'unset') {
			from = '';
			to = '';
		} else if (op === 'before') {
			from = '';
		} else if (op === 'after') {
			to = '';
		}
		emit();
	}
</script>

<div class="flex flex-col space-y-1">
	<span class="text-sm font-semibold" id="{field}-date-filter">{label}</span>
	<div class="flex flex-wrap items-center gap-2">
		<select
			class="select w-fit text-sm"
			aria-labelledby="{field}-date-filter"
			value={op}
			onchange={(e) => selectOperator(e.currentTarget.value)}
		>
			{#each OPERATORS as operator}
				<option value={operator.value}>{operator.label}</option>
			{/each}
		</select>
		{#if op === 'after' || op === 'between'}
			<input
				type="date"
				class="input w-fit text-sm"
				aria-label="{label} - {m.onOrAfter()}"
				bind:value={from}
				onchange={emit}
			/>
		{/if}
		{#if op === 'between'}
			<span class="text-sm">{m.and()}</span>
		{/if}
		{#if op === 'before' || op === 'between'}
			<input
				type="date"
				class="input w-fit text-sm"
				aria-label="{label} - {m.onOrBefore()}"
				bind:value={to}
				onchange={emit}
			/>
		{/if}
	</div>
</div>
