<script lang="ts">
	// Editor for a derived metric's datasets: each one names a readable
	// model, filters its rows (an "or" of "and" groups, the same shape the
	// workflow builder edits) and lists the aggregates to compute. The value
	// is the backend's own read configuration, keyed by dataset name.
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import {
		aliasOf,
		datasetNameProblem,
		sanitizeDatasetName,
		type AggregateRow
	} from '$lib/utils/derived-metrics';
	import {
		newCondition,
		treeToGroups,
		groupsToTree,
		FILTER_OPS,
		type Condition
	} from '$lib/utils/filter-dnf';

	export interface AggregateFn {
		name: string;
		engine: string;
		needs_field: boolean;
		accepts: string[];
		params: string[];
	}
	export interface ReadableModel {
		key: string;
		fields: string[];
		kinds?: Record<string, string>;
		annotations?: string[];
		// Fields with a fixed set of values: the only ones a derived metric
		// may group by.
		categorical?: string[];
		computed?: string[];
		aggregates?: AggregateFn[];
	}
	interface Dataset {
		name: string;
		// What the author typed while it cannot be applied (empty, taken).
		nameDraft?: string;
		nameProblem?: 'required' | 'invalid' | 'taken' | null;
		model: string;
		groups: Condition[][];
		aggregates: AggregateRow[];
		rawFilters: Record<string, unknown> | null;
	}

	interface Props {
		value: Record<string, unknown> | null | undefined;
		models: ReadableModel[];
		onchange?: () => void;
	}
	let { value = $bindable(), models, onchange }: Props = $props();

	// Operators a field kind can carry (mirrors core.reads.filters).
	const KIND_OPS: Record<string, string[]> = {
		bool: ['eq', 'neq', 'is_null'],
		relation: ['eq', 'neq', 'in', 'not_in', 'is_null'],
		numeric: FILTER_OPS.filter((op) => op !== 'contains'),
		date: FILTER_OPS.filter((op) => op !== 'contains'),
		text: FILTER_OPS
	};

	let datasets = $state<Dataset[]>([]);
	let lastEmitted = '';

	type StoredConfig = {
		model?: unknown;
		filters?: Record<string, unknown> | null;
		aggregates?: unknown;
	};

	function fromValue(raw: Record<string, unknown> | null | undefined): Dataset[] {
		if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return [];
		return Object.entries(raw).map(([name, config]) => {
			const cfg: StoredConfig =
				config && typeof config === 'object' ? (config as StoredConfig) : {};
			const groups = treeToGroups(cfg.filters);
			return {
				name,
				model: typeof cfg.model === 'string' ? cfg.model : (models[0]?.key ?? ''),
				groups: groups ?? [],
				// A tree the builder cannot edit (a "not" group) is kept as is.
				rawFilters: groups === null ? (cfg.filters ?? null) : null,
				aggregates: Array.isArray(cfg.aggregates)
					? (cfg.aggregates as AggregateRow[]).map((a) => ({ ...a }))
					: [{ fn: 'count' }]
			};
		});
	}

	function toValue(list: Dataset[]): Record<string, unknown> {
		const out: Record<string, unknown> = {};
		for (const d of list) {
			const config: Record<string, unknown> = { model: d.model };
			const filters = d.rawFilters ?? groupsToTree(d.groups);
			if (filters && Object.keys(filters).length) config.filters = filters;
			config.aggregates = d.aggregates.map((a) => {
				const row: Record<string, unknown> = { fn: a.fn };
				if (a.field) row.field = a.field;
				if (a.group_by) row.group_by = a.group_by;
				if (a.as) row.as = a.as;
				if (a.p !== undefined && a.p !== null && a.p !== ('' as unknown)) row.p = a.p;
				return row;
			});
			out[d.name] = config;
		}
		return out;
	}

	// The stored value drives the editor until the editor writes it back;
	// comparing serialized forms keeps the two from feeding each other.
	$effect(() => {
		const serialized = JSON.stringify(value ?? null);
		if (serialized !== lastEmitted) {
			datasets = fromValue(value);
			lastEmitted = serialized;
		}
	});

	function emit() {
		const next = toValue(datasets);
		lastEmitted = JSON.stringify(next);
		value = Object.keys(next).length ? next : null;
		onchange?.();
	}

	function entryFor(d: Dataset): ReadableModel | undefined {
		return models.find((entry) => entry.key === d.model);
	}

	function opsFor(d: Dataset, field: string): string[] {
		const kind = entryFor(d)?.kinds?.[field];
		return kind ? (KIND_OPS[kind] ?? FILTER_OPS) : FILTER_OPS;
	}

	function uniqueName(base: string): string {
		const taken = new Set(datasets.map((d) => d.name));
		if (!taken.has(base)) return base;
		let index = 2;
		while (taken.has(`${base}_${index}`)) index += 1;
		return `${base}_${index}`;
	}

	function addDataset() {
		const model = models[0]?.key ?? '';
		datasets.push({
			name: uniqueName(model.replace(/[^A-Za-z0-9_]/g, '_') || 'dataset'),
			model,
			groups: [],
			aggregates: [{ fn: 'count' }],
			rawFilters: null
		});
		emit();
	}

	function setModel(d: Dataset, model: string) {
		d.model = model;
		// Field whitelists differ per model: stale filters and aggregates
		// would fail validation.
		d.groups = [];
		d.rawFilters = null;
		d.aggregates = [{ fn: 'count' }];
		emit();
	}

	function setName(d: Dataset, raw: string) {
		const name = sanitizeDatasetName(raw);
		const problem = datasetNameProblem(
			name,
			datasets.filter((other) => other !== d).map((other) => other.name)
		);
		d.nameDraft = name;
		d.nameProblem = problem;
		// The stored value keeps the last valid name until this one is.
		if (problem) return;
		d.name = name;
		emit();
	}

	const NAME_PROBLEM_MESSAGES = {
		required: () => m.datasetNameRequired(),
		invalid: () => m.datasetNameInvalid(),
		taken: () => m.datasetNameTaken()
	};

	// ----- aggregates (same rules as the workflow builder) -----

	function aggregateFn(d: Dataset, name: string): AggregateFn | undefined {
		return entryFor(d)?.aggregates?.find((fn) => fn.name === name);
	}

	function aggregateFieldChoices(
		d: Dataset,
		fnName: string
	): { value: string; label: string; worker: boolean }[] {
		const entry = entryFor(d);
		const fn = aggregateFn(d, fnName);
		if (!entry || !fn || !fn.needs_field) return [];
		const kinds = entry.kinds ?? {};
		const columns = entry.fields
			.filter((field) => fn.accepts.includes(kinds[field] ?? ''))
			.map((field) => ({ value: field, label: field, worker: false }));
		if (fn.name === 'count_distinct') return columns;
		const computed = (entry.computed ?? [])
			.filter((name) => !entry.fields.includes(name))
			.map((name) => ({
				value: name,
				label: `${name} (${m.aggregateComputedValue()})`,
				worker: true
			}));
		return [...columns, ...computed];
	}

	function groupChoices(d: Dataset): string[] {
		const entry = entryFor(d);
		if (!entry) return [];
		// A derived value is visible without the viewer's read rights on the
		// rows: group by categories, never by free text.
		if (entry.categorical) return entry.categorical;
		const annotations = new Set(entry.annotations ?? []);
		return entry.fields.filter((field) => !annotations.has(field));
	}

	function runsInWorker(d: Dataset, row: AggregateRow): boolean {
		const fn = aggregateFn(d, row.fn);
		if (!fn) return false;
		if (fn.engine === 'python') return true;
		return !!row.field && !entryFor(d)?.fields.includes(row.field);
	}

	function setFn(d: Dataset, row: AggregateRow, name: string) {
		row.fn = name;
		const fn = aggregateFn(d, name);
		if (!fn?.needs_field) delete row.field;
		else if (row.field && !aggregateFieldChoices(d, name).some((c) => c.value === row.field))
			delete row.field;
		if (!fn?.params.includes('p')) delete row.p;
		else if (row.p === undefined) row.p = 90;
		emit();
	}

	function setRowKey(row: AggregateRow, key: 'field' | 'group_by' | 'as', text: string) {
		if (text) row[key] = key === 'as' ? text.replace(/[^A-Za-z0-9_]/g, '_') : text;
		else delete row[key];
		emit();
	}
</script>

<div class="flex flex-col gap-3">
	{#each datasets as d, dIndex (dIndex)}
		<div
			class="rounded-base border border-surface-200-800 bg-surface-50-950 p-3 flex flex-col gap-2"
		>
			<div class="flex items-end gap-2">
				<label class="flex flex-col gap-1 w-40 shrink-0">
					<span class="text-xs font-semibold">{m.datasetName()}</span>
					<input
						type="text"
						class="input text-sm font-mono"
						value={d.nameDraft ?? d.name}
						oninput={(e) => setName(d, e.currentTarget.value)}
						aria-invalid={d.nameProblem ? 'true' : undefined}
						data-testid="dataset-name"
					/>
					{#if d.nameProblem}
						<span class="text-xs text-error-500" data-testid="dataset-name-error">
							{NAME_PROBLEM_MESSAGES[d.nameProblem]()}
						</span>
					{/if}
				</label>
				<label class="flex flex-col gap-1 flex-1 min-w-0">
					<span class="text-xs font-semibold">{m.objectToRead()}</span>
					<select
						class="select text-sm w-full"
						value={d.model}
						onchange={(e) => setModel(d, e.currentTarget.value)}
					>
						{#each models as entry (entry.key)}
							<option value={entry.key}>{safeTranslate(entry.key)}</option>
						{/each}
					</select>
				</label>
				<button
					type="button"
					title={m.delete()}
					aria-label={m.delete()}
					class="btn-icon preset-tonal w-7 h-7 text-xs shrink-0 hover:preset-filled-error-500"
					onclick={() => {
						datasets.splice(dIndex, 1);
						emit();
					}}
				>
					<i class="fa-solid fa-trash"></i>
				</button>
			</div>

			<div class="flex flex-col gap-1">
				<span class="text-xs font-semibold">{m.readFilters()}</span>
				{#if d.rawFilters}
					<p class="text-xs text-surface-500">{m.datasetFiltersNotEditable()}</p>
					<pre class="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(d.rawFilters)}</pre>
				{:else}
					<div class="flex flex-col gap-2">
						{#each d.groups as group, groupIndex (groupIndex)}
							{#if groupIndex > 0}
								<div class="flex items-center gap-2">
									<hr class="grow border-surface-200-800" />
									<span class="text-[10px] font-semibold uppercase text-surface-500">{m.or()}</span>
									<hr class="grow border-surface-200-800" />
								</div>
							{/if}
							<div class="flex flex-col gap-2 rounded-base border border-surface-200-800 p-2">
								<div class="flex items-center gap-2">
									<span class="text-[10px] uppercase tracking-wide text-surface-500">
										{m.matchAllConditions()}
									</span>
									<button
										type="button"
										title={m.delete()}
										aria-label={m.delete()}
										class="btn-icon preset-tonal w-5 h-5 text-[9px] ml-auto hover:preset-filled-error-500"
										onclick={() => {
											d.groups.splice(groupIndex, 1);
											emit();
										}}
									>
										<i class="fa-solid fa-trash"></i>
									</button>
								</div>
								{#each group as condition, conditionIndex (conditionIndex)}
									<div
										class="flex flex-col gap-1.5 rounded-base border border-surface-200-800 p-1.5"
									>
										<div class="flex items-center gap-1">
											<select
												class="select text-xs flex-1 min-w-0"
												bind:value={condition.field}
												onchange={() => {
													if (!opsFor(d, condition.field).includes(condition.op))
														condition.op = 'eq';
													emit();
												}}
											>
												{#if !condition.field}
													<option value="">—</option>
												{/if}
												{#each entryFor(d)?.fields ?? [] as field (field)}
													<option value={field}>{field}</option>
												{/each}
											</select>
											<select
												class="select text-xs w-24 shrink-0"
												bind:value={condition.op}
												onchange={emit}
											>
												{#each opsFor(d, condition.field) as op (op)}
													<option value={op}>{op}</option>
												{/each}
											</select>
											<button
												type="button"
												title={m.delete()}
												aria-label={m.delete()}
												class="btn-icon preset-tonal w-5 h-5 text-[9px] shrink-0 hover:preset-filled-error-500"
												onclick={() => {
													group.splice(conditionIndex, 1);
													emit();
												}}
											>
												<i class="fa-solid fa-xmark"></i>
											</button>
										</div>
										{#if condition.op !== 'is_null'}
											<input
												type="text"
												class="input text-xs w-full"
												placeholder={condition.op === 'in' || condition.op === 'not_in'
													? 'a, b, c'
													: m.datasetValuePlaceholder()}
												bind:value={condition.value}
												oninput={emit}
											/>
										{/if}
									</div>
								{/each}
								<button
									type="button"
									class="btn preset-tonal text-[10px] self-start"
									onclick={() => {
										group.push(newCondition());
										emit();
									}}
								>
									<i class="fa-solid fa-plus mr-1"></i>{m.addCondition()}
								</button>
							</div>
						{/each}
						<button
							type="button"
							class="btn preset-tonal text-[10px] self-start"
							onclick={() => {
								d.groups.push([newCondition()]);
								emit();
							}}
						>
							<i class="fa-solid fa-plus mr-1"></i>{m.addConditionGroup()}
						</button>
					</div>
				{/if}
			</div>

			<div class="flex flex-col gap-1">
				<span class="text-xs font-semibold">{m.readAggregates()}</span>
				<div class="flex flex-col gap-2">
					{#each d.aggregates as row, rowIndex (rowIndex)}
						<div class="flex flex-col gap-1.5 rounded-base border border-surface-200-800 p-2">
							<div class="flex items-center gap-1">
								<select
									class="select text-xs flex-1 min-w-0"
									value={row.fn}
									onchange={(e) => setFn(d, row, e.currentTarget.value)}
								>
									{#each entryFor(d)?.aggregates ?? [] as fn (fn.name)}
										<option value={fn.name}>{safeTranslate(`aggregate_${fn.name}`)}</option>
									{/each}
								</select>
								{#if aggregateFn(d, row.fn)?.needs_field}
									<select
										class="select text-xs flex-1 min-w-0"
										value={row.field ?? ''}
										onchange={(e) => setRowKey(row, 'field', e.currentTarget.value)}
									>
										<option value="">—</option>
										{#each aggregateFieldChoices(d, row.fn) as choice (choice.value)}
											<option value={choice.value}>{choice.label}</option>
										{/each}
									</select>
								{/if}
								<button
									type="button"
									title={m.delete()}
									aria-label={m.delete()}
									class="btn-icon preset-tonal w-5 h-5 text-[9px] shrink-0 hover:preset-filled-error-500"
									onclick={() => {
										d.aggregates.splice(rowIndex, 1);
										emit();
									}}
								>
									<i class="fa-solid fa-xmark"></i>
								</button>
							</div>
							<div class="flex items-center gap-1">
								<select
									class="select text-xs flex-1 min-w-0"
									title={m.aggregateGroupBy()}
									value={row.group_by ?? ''}
									onchange={(e) => setRowKey(row, 'group_by', e.currentTarget.value)}
								>
									<option value="">{m.aggregateNoGroup()}</option>
									{#each groupChoices(d) as field (field)}
										<option value={field}>{m.aggregateGroupBy()}: {field}</option>
									{/each}
								</select>
								{#if aggregateFn(d, row.fn)?.params.includes('p')}
									<input
										type="number"
										min="0"
										max="100"
										class="input text-xs w-16 shrink-0"
										title={m.aggregatePercentile()}
										bind:value={row.p}
										oninput={emit}
									/>
								{/if}
								<input
									type="text"
									class="input text-xs w-28 shrink-0 font-mono"
									placeholder={m.aggregateAlias()}
									value={row.as ?? ''}
									oninput={(e) => setRowKey(row, 'as', e.currentTarget.value)}
								/>
							</div>
							<div class="flex items-center justify-between gap-2">
								<span class="text-[10px] text-surface-500 font-mono">
									{m.referenceInExpression()}: {d.name}.{aliasOf(row)}
								</span>
								{#if runsInWorker(d, row)}
									<span class="text-[10px] text-warning-600-400">{m.aggregateRunsInWorker()}</span>
								{/if}
							</div>
						</div>
					{/each}
					<button
						type="button"
						class="btn preset-tonal text-[10px] self-start"
						onclick={() => {
							d.aggregates.push({ fn: 'count' });
							emit();
						}}
					>
						<i class="fa-solid fa-plus mr-1"></i>{m.addAggregate()}
					</button>
				</div>
			</div>
		</div>
	{/each}
	{#if !datasets.length}
		<p class="text-xs text-surface-500">{m.noDatasetsYet()}</p>
	{/if}
	<button type="button" class="btn preset-tonal text-xs self-start" onclick={addDataset}>
		<i class="fa-solid fa-plus mr-1"></i>{m.addDataset()}
	</button>
</div>
