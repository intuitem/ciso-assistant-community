<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Condition {
		field: string;
		op: string;
		value: string;
		changed: boolean;
	}

	interface EventKey {
		key: string;
		model: string;
		action: string;
	}

	interface Props {
		workflowId: string;
		folders?: { id: string; name: string }[];
	}

	let { workflowId, folders = [] }: Props = $props();

	const OPS = ['eq', 'neq', 'gt', 'lt', 'gte', 'lte', 'in', 'not_in', 'contains', 'is_null'];
	const FIELD_CHIPS = ['status', 'folder', 'filtering_labels'];
	const CHANGED_HELP =
		'Match the transition (field just changed to this value), not the standing state.';

	let triggers = $state<any[]>([]);
	let eventKeys = $state<EventKey[]>([]);
	let loading = $state(true);
	let error = $state('');
	let editingId = $state<string | null>(null);

	let form = $state({ name: '', event_key: '' });
	let groups = $state<Condition[][]>([]);
	let rawMode = $state(false);
	let rawJson = $state('{}');

	const eventKeysByModel = $derived.by(() => {
		const map = new Map<string, EventKey[]>();
		for (const ek of eventKeys) {
			if (!map.has(ek.model)) map.set(ek.model, []);
			map.get(ek.model)!.push(ek);
		}
		return [...map.entries()];
	});

	function opsUrl(action: string) {
		return `/workflows/${workflowId}/ops?action=${action}`;
	}

	async function ops(action: string, body: Record<string, unknown>) {
		return fetch(opsUrl(action), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
	}

	// Backend validation errors arrive as message keys (e.g. invalidEventKey).
	function localizeError(data: any): string {
		const first = Object.values(data ?? {}).flat()[0];
		const key = typeof first === 'string' ? first : '';
		return (m as any)[key]?.() ?? (key || m.anErrorOccurred());
	}

	export async function refresh() {
		const res = await ops('list-event-triggers', { workflow: workflowId });
		if (res.ok) {
			const data = await res.json();
			triggers = data.results ?? data;
		}
		loading = false;
	}

	async function loadEventKeys() {
		const res = await ops('event-trigger-keys', {});
		if (res.ok) {
			const data = await res.json();
			eventKeys = data.results ?? data;
		}
	}

	// --- DNF <-> filter tree mapping -------------------------------------

	function newCondition(): Condition {
		return { field: '', op: 'eq', value: '', changed: false };
	}

	function conditionsFrom(list: any[]): Condition[] {
		return list.map((c: any) => ({
			field: c.field ?? '',
			op: c.op ?? 'eq',
			value:
				c.value === undefined || c.value === null
					? ''
					: typeof c.value === 'string'
						? c.value
						: JSON.stringify(c.value),
			changed: !!c.changed
		}));
	}

	// Returns the DNF groups, or null when the tree doesn't fit the
	// "or of and-groups" shape (deeper nesting, "not", ...).
	function treeToGroups(tree: any): Condition[][] | null {
		if (tree === null || tree === undefined) return [];
		if (typeof tree !== 'object' || Array.isArray(tree)) return null;
		if (Object.keys(tree).length === 0) return [];
		const conditions = Array.isArray(tree.conditions) ? tree.conditions : [];
		const children = Array.isArray(tree.children) ? tree.children : [];
		if (tree.operator === 'and') {
			if (children.length) return null;
			return [conditionsFrom(conditions)];
		}
		if (tree.operator === 'or') {
			const out: Condition[][] = [];
			for (const child of children) {
				if (
					!child ||
					typeof child !== 'object' ||
					child.operator !== 'and' ||
					(Array.isArray(child.children) ? child.children : []).length
				) {
					return null;
				}
				out.push(conditionsFrom(Array.isArray(child.conditions) ? child.conditions : []));
			}
			// Root-level conditions on an "or" node each count as one extra group.
			for (const cond of conditions) out.push(conditionsFrom([cond]));
			return out;
		}
		return null;
	}

	// "3" -> 3, "true" -> true, "[1,2]" -> [1,2]; anything unparseable stays a string.
	function parseValue(raw: string): unknown {
		const trimmed = raw.trim();
		if (!trimmed) return raw;
		try {
			return JSON.parse(trimmed);
		} catch {
			return raw;
		}
	}

	function serializeCondition(c: Condition): Record<string, unknown> {
		const out: Record<string, unknown> = { field: c.field.trim(), op: c.op };
		if (c.op !== 'is_null') out.value = parseValue(c.value);
		if (c.changed) out.changed = true;
		return out;
	}

	function groupsToTree(dnf: Condition[][]): Record<string, unknown> {
		const serialized = dnf
			.map((group) => group.filter((c) => c.field.trim()).map(serializeCondition))
			.filter((group) => group.length);
		if (!serialized.length) return {};
		if (serialized.length === 1) return { operator: 'and', conditions: serialized[0] };
		return {
			operator: 'or',
			conditions: [],
			children: serialized.map((conditions) => ({ operator: 'and', conditions }))
		};
	}

	function countConditions(tree: any): number {
		if (!tree || typeof tree !== 'object') return 0;
		let count = Array.isArray(tree.conditions) ? tree.conditions.length : 0;
		for (const child of Array.isArray(tree.children) ? tree.children : []) {
			count += countConditions(child);
		}
		return count;
	}

	function filterSummary(tree: any): string {
		const conditions = countConditions(tree);
		if (!conditions) return '';
		const dnf = treeToGroups(tree);
		return dnf ? `${conditions} · ${dnf.length}` : `${conditions}`;
	}

	// --- form lifecycle ---------------------------------------------------

	function resetForm() {
		form = { name: '', event_key: '' };
		groups = [];
		rawMode = false;
		rawJson = '{}';
	}

	async function submit(event: Event) {
		event.preventDefault();
		error = '';
		let filters: unknown;
		if (rawMode) {
			try {
				filters = JSON.parse(rawJson);
			} catch {
				error = m.invalidFieldFilters();
				return;
			}
		} else {
			filters = groupsToTree(groups);
		}
		const payload = { ...form, filters, workflow: workflowId };
		const res = editingId
			? await ops('update-event-trigger', { id: editingId, patch: { ...form, filters } })
			: await ops('create-event-trigger', payload);
		if (!res.ok) {
			error = localizeError(await res.json().catch(() => ({})));
			return;
		}
		resetForm();
		editingId = null;
		await refresh();
	}

	function startEdit(trigger: any) {
		editingId = trigger.id;
		form = { name: trigger.name, event_key: trigger.event_key };
		const dnf = treeToGroups(trigger.filters);
		if (dnf === null) {
			rawMode = true;
			rawJson = JSON.stringify(trigger.filters ?? {}, null, 2);
			groups = [];
		} else {
			rawMode = false;
			rawJson = '{}';
			groups = dnf;
		}
		error = '';
	}

	function cancelEdit() {
		editingId = null;
		resetForm();
		error = '';
	}

	async function toggleEnabled(trigger: any) {
		const res = await ops('update-event-trigger', {
			id: trigger.id,
			patch: { enabled: !trigger.enabled }
		});
		if (res.ok) await refresh();
	}

	async function remove(id: string) {
		const res = await ops('delete-event-trigger', { id });
		if (res.ok) {
			if (editingId === id) cancelEdit();
			await refresh();
		}
	}

	$effect(() => {
		refresh();
		loadEventKeys();
	});

	const RESULT_BADGE: Record<string, { class: string; label: () => string }> = {
		triggered: { class: 'preset-tonal-success', label: () => m.triggerResultTriggered() },
		skipped_unpublished: {
			class: 'preset-tonal-warning',
			label: () => m.triggerResultSkippedUnpublished()
		},
		skipped_depth: {
			class: 'preset-tonal-warning',
			label: () => m.triggerResultSkippedDepth()
		},
		error: { class: 'preset-tonal-error', label: () => m.triggerResultError() }
	};

	function formatWhen(iso: string | null): string {
		if (!iso) return '—';
		return new Date(iso).toLocaleString();
	}

	function relativeTime(iso: string | null): string {
		if (!iso) return '—';
		const diff = new Date(iso).getTime() - Date.now();
		const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
		const units: [Intl.RelativeTimeFormatUnit, number][] = [
			['day', 86400000],
			['hour', 3600000],
			['minute', 60000]
		];
		for (const [unit, ms] of units) {
			if (Math.abs(diff) >= ms) return rtf.format(Math.round(diff / ms), unit);
		}
		return rtf.format(0, 'minute');
	}
</script>

<div
	class="h-80 shrink-0 border-t border-surface-200-800 bg-surface-100-900 overflow-y-auto"
	data-testid="event-triggers-panel"
>
	<form class="flex flex-col gap-2 px-4 pt-3 pb-2" onsubmit={submit}>
		<div class="flex items-end gap-2">
			<label class="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-surface-500">
				{m.name()}
				<input
					type="text"
					class="input text-xs w-36"
					bind:value={form.name}
					required
					data-testid="event-trigger-name"
				/>
			</label>
			<label class="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-surface-500">
				{m.whenThisHappens()}
				<select
					class="select text-xs w-56"
					bind:value={form.event_key}
					required
					data-testid="event-trigger-key"
				>
					<option value="" disabled hidden></option>
					{#each eventKeysByModel as [model, keys] (model)}
						<optgroup label={safeTranslate(model)}>
							{#each keys as ek (ek.key)}
								<option value={ek.key}>{ek.action}</option>
							{/each}
						</optgroup>
					{/each}
				</select>
			</label>
			<button
				type="submit"
				class="btn preset-filled-primary-500 text-xs"
				data-testid="add-event-trigger"
			>
				{#if editingId}
					<i class="fa-solid fa-check mr-1"></i>{m.save()}
				{:else}
					<i class="fa-solid fa-plus mr-1"></i>{m.addEventTrigger()}
				{/if}
			</button>
			{#if editingId}
				<button type="button" class="btn preset-tonal text-xs" onclick={cancelEdit}>
					{m.cancel()}
				</button>
			{/if}
			{#if error}
				<span class="text-xs text-error-500 pb-2">{error}</span>
			{/if}
		</div>

		{#if rawMode}
			<label class="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-surface-500">
				{m.rawJsonFilters()}
				<textarea class="textarea text-xs font-mono w-full" rows="6" bind:value={rawJson}
				></textarea>
			</label>
		{:else}
			<div class="flex flex-col gap-2">
				<span class="text-[10px] uppercase tracking-wide text-surface-500">
					{m.matchAnyGroup()}
				</span>
				{#each groups as group, groupIndex (groupIndex)}
					{#if groupIndex > 0}
						<div class="flex items-center gap-2">
							<hr class="grow border-surface-200-800" />
							<span class="text-[10px] font-semibold uppercase text-surface-500">
								{m.or()}
							</span>
							<hr class="grow border-surface-200-800" />
						</div>
					{/if}
					<div
						class="flex flex-col gap-2 rounded-base border border-surface-200-800 bg-surface-50-950 p-2"
					>
						<div class="flex items-center gap-2">
							<span class="text-[10px] uppercase tracking-wide text-surface-500">
								{m.matchAllConditions()}
							</span>
							<button
								type="button"
								title={m.delete()}
								class="btn-icon preset-tonal w-5 h-5 text-[9px] ml-auto hover:preset-filled-error-500"
								onclick={() => groups.splice(groupIndex, 1)}
							>
								<i class="fa-solid fa-trash"></i>
							</button>
						</div>
						{#each group as condition, conditionIndex (conditionIndex)}
							<div class="flex items-end gap-2">
								<div class="flex flex-col gap-1">
									<div class="flex gap-1">
										{#each FIELD_CHIPS as chip (chip)}
											<button
												type="button"
												class="badge preset-tonal text-[9px] cursor-pointer"
												onclick={() => (condition.field = chip)}
											>
												{chip}
											</button>
										{/each}
									</div>
									<input
										type="text"
										class="input text-xs w-40 font-mono"
										bind:value={condition.field}
									/>
								</div>
								<select class="select text-xs w-28" bind:value={condition.op}>
									{#each OPS as op (op)}
										<option value={op}>{op}</option>
									{/each}
								</select>
								{#if condition.op !== 'is_null'}
									{#if condition.field === 'folder'}
										<select class="select text-xs w-40" bind:value={condition.value}>
											{#each folders as folder (folder.id)}
												<option value={folder.id}>{folder.name}</option>
											{/each}
										</select>
									{:else}
										<input type="text" class="input text-xs w-40" bind:value={condition.value} />
									{/if}
								{/if}
								<label
									class="flex items-center gap-1 pb-2 text-[10px] text-surface-500"
									title={CHANGED_HELP}
								>
									<input type="checkbox" class="checkbox" bind:checked={condition.changed} />
									{m.onlyWhenChanged()}
								</label>
								<button
									type="button"
									title={m.delete()}
									class="btn-icon preset-tonal w-6 h-6 text-[10px] hover:preset-filled-error-500"
									onclick={() => group.splice(conditionIndex, 1)}
								>
									<i class="fa-solid fa-xmark"></i>
								</button>
							</div>
						{/each}
						<button
							type="button"
							class="btn preset-tonal text-[10px] self-start"
							onclick={() => group.push(newCondition())}
						>
							<i class="fa-solid fa-plus mr-1"></i>{m.addCondition()}
						</button>
					</div>
				{/each}
				<button
					type="button"
					class="btn preset-tonal text-[10px] self-start"
					onclick={() => groups.push([newCondition()])}
				>
					<i class="fa-solid fa-plus mr-1"></i>{m.addConditionGroup()}
				</button>
			</div>
		{/if}
	</form>

	{#if loading}
		<p class="p-4 text-xs text-surface-500">
			<i class="fa-solid fa-spinner fa-spin mr-1"></i>
		</p>
	{:else if !triggers.length}
		<p class="p-4 text-xs text-surface-500 text-center">
			<i class="fa-solid fa-bolt block text-lg mb-2 opacity-40"></i>
			{m.noEventTriggersYet()}
		</p>
	{:else}
		<ul class="divide-y divide-surface-200-800">
			{#each triggers as trigger (trigger.id)}
				{@const badge = RESULT_BADGE[trigger.last_result]}
				{@const summary = filterSummary(trigger.filters)}
				<li class="flex items-center gap-3 px-4 py-2 text-xs">
					<button
						type="button"
						role="switch"
						aria-checked={trigger.enabled}
						title={m.enabled()}
						class="btn-icon w-6 h-6 text-[10px] {trigger.enabled
							? 'preset-filled-success-500'
							: 'preset-tonal'}"
						onclick={() => toggleEnabled(trigger)}
						data-testid="toggle-event-trigger"
					>
						<i class="fa-solid {trigger.enabled ? 'fa-play' : 'fa-pause'}"></i>
					</button>
					<span class="font-semibold text-surface-800-200 truncate">{trigger.name}</span>
					<span class="badge preset-tonal font-mono text-[9px]">{trigger.event_key}</span>
					{#if summary}
						<span class="text-surface-500">
							<i class="fa-solid fa-filter mr-1 opacity-60"></i>{summary}
						</span>
					{/if}
					<span
						class="text-surface-500"
						title="{m.triggerLastFired()}: {formatWhen(trigger.last_triggered_at)}"
					>
						<i class="fa-regular fa-clock mr-1"></i>{relativeTime(trigger.last_triggered_at)}
					</span>
					{#if badge}
						<span
							class="badge {badge.class} text-[9px]"
							title={formatWhen(trigger.last_triggered_at)}
						>
							{badge.label()}
						</span>
					{/if}
					<span class="ml-auto flex items-center gap-1 shrink-0">
						<button
							type="button"
							title={m.edit()}
							class="btn-icon preset-tonal w-6 h-6 text-[10px]"
							onclick={() => startEdit(trigger)}
							data-testid="edit-event-trigger"
						>
							<i class="fa-solid fa-pen"></i>
						</button>
						<button
							type="button"
							title={m.delete()}
							class="btn-icon preset-tonal w-6 h-6 text-[10px] hover:preset-filled-error-500"
							onclick={() => remove(trigger.id)}
							data-testid="delete-event-trigger"
						>
							<i class="fa-solid fa-trash"></i>
						</button>
					</span>
				</li>
			{/each}
		</ul>
	{/if}
</div>
