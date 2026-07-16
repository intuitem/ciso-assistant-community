<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';
	import type { EntityPickerOptions } from '$lib/utils/entityPicker';

	// Canonical picker types live in entityPicker.ts; the modal just adds the
	// Skeleton-injected `parent`.
	type Props = EntityPickerOptions & { parent: any };

	let {
		parent,
		endpoint,
		title,
		subtitle,
		labelField = 'str',
		secondaryField,
		columns = [],
		scopeFilters = {},
		activeField,
		initialSelectedIds = [],
		initialSelectedParams,
		confirmLabel,
		onConfirm
	}: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

	const selected = new SvelteMap<string, any>();
	let rows = $state<any[]>([]);
	let count = $state(0);
	let offset = $state(0);
	let pageSize = $state(10);
	let query = $state('');
	let columnFilters = $state<Record<string, string>>({});
	let includeInactive = $state(false);
	let mode = $state<'list' | 'table'>('list');
	let loading = $state(false);
	let loadError = $state(false);
	let saving = $state(false);
	let saveError = $state(false);
	// Server-side sort: the column key, prefixed with '-' for descending. Empty = default.
	let ordering = $state('');
	let debounce: ReturnType<typeof setTimeout> | null = null;
	// Monotonic request id: a slow earlier response must not overwrite a newer one.
	let loadSeq = 0;

	function buildParams(extra: Record<string, string> = {}) {
		const p = new URLSearchParams();
		for (const [k, v] of Object.entries(scopeFilters)) if (v != null && v !== '') p.set(k, v);
		if (activeField && !includeInactive) p.set(activeField, 'true');
		if (query.trim()) p.set('search', query.trim());
		for (const [k, v] of Object.entries(columnFilters)) {
			if (!v) continue;
			const col = columns.find((c) => c.key === k);
			p.set(col?.filter === 'exact' ? k : `${k}__icontains`, v);
		}
		if (ordering) p.set('ordering', ordering);
		for (const [k, v] of Object.entries(extra)) p.set(k, v);
		return p;
	}

	function toggleSort(key: string) {
		// asc -> desc -> off
		ordering = ordering === key ? `-${key}` : ordering === `-${key}` ? '' : key;
		reloadFromStart();
	}

	function sortIcon(key: string): string {
		if (ordering === key) return 'fa-sort-up';
		if (ordering === `-${key}`) return 'fa-sort-down';
		return 'fa-sort';
	}

	async function load() {
		const seq = ++loadSeq;
		loading = true;
		loadError = false;
		try {
			const p = buildParams({ limit: String(pageSize), offset: String(offset) });
			const res = await fetch(`/${endpoint}/autocomplete?${p.toString()}`);
			if (seq !== loadSeq) return; // superseded by a newer request
			if (res.ok) {
				const data = await res.json();
				if (seq !== loadSeq) return;
				rows = data?.results ?? data ?? [];
				count = data?.count ?? rows.length;
			} else {
				loadError = true;
			}
		} catch {
			if (seq === loadSeq) loadError = true;
		} finally {
			if (seq === loadSeq) loading = false;
		}
	}

	async function hydrateSelection() {
		let p: URLSearchParams;
		if (initialSelectedIds.length) {
			p = new URLSearchParams({ id: initialSelectedIds.join(','), limit: '10000' });
		} else if (initialSelectedParams) {
			p = new URLSearchParams({ ...initialSelectedParams, limit: '10000' });
		} else {
			return;
		}
		try {
			const res = await fetch(`/${endpoint}/autocomplete?${p.toString()}`);
			if (res.ok) {
				const data = await res.json();
				for (const o of data?.results ?? data ?? []) selected.set(o.id, o);
			} else {
				console.error(`Failed to hydrate ${endpoint} selection:`, res.status);
				loadError = true;
			}
		} catch (e) {
			console.error(`Failed to hydrate ${endpoint} selection:`, e);
			loadError = true;
		}
	}

	function reloadFromStart() {
		offset = 0;
		load();
	}

	function onSearch(value: string) {
		query = value;
		if (debounce) clearTimeout(debounce);
		debounce = setTimeout(reloadFromStart, 200);
	}

	function onColumnFilter(key: string, value: string) {
		columnFilters = { ...columnFilters, [key]: value };
		if (debounce) clearTimeout(debounce);
		debounce = setTimeout(reloadFromStart, 200);
	}

	function toggleInactive() {
		includeInactive = !includeInactive;
		reloadFromStart();
	}

	function toggle(row: any) {
		if (selected.has(row.id)) selected.delete(row.id);
		else selected.set(row.id, row);
	}

	// Select/deselect all rows on the current page (selection persists across pages).
	const pageAllSelected = $derived(rows.length > 0 && rows.every((r) => selected.has(r.id)));

	function toggleSelectAllPage() {
		if (pageAllSelected) rows.forEach((r) => selected.delete(r.id));
		else rows.forEach((r) => selected.set(r.id, r));
	}

	function label(o: any): string {
		return o?.[labelField] ?? o?.str ?? o?.email ?? o?.id ?? '';
	}

	function initials(o: any): string {
		// Prefer the display string (name) so avatars stay meaningful even when the
		// primary label is the email.
		const parts = String(o?.str ?? label(o))
			.trim()
			.split(/\s+/)
			.filter(Boolean);
		if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
		return (parts[0]?.slice(0, 2) ?? '?').toUpperCase();
	}

	const pageEnd = $derived(Math.min(offset + pageSize, count));
	const hasPrev = $derived(offset > 0);
	const hasNext = $derived(offset + pageSize < count);

	function prev() {
		if (!hasPrev) return;
		offset = Math.max(0, offset - pageSize);
		load();
	}
	function next() {
		if (!hasNext) return;
		offset = offset + pageSize;
		load();
	}

	function setPageSize(n: number) {
		pageSize = n;
		offset = 0;
		load();
	}

	async function confirm() {
		saving = true;
		saveError = false;
		try {
			await onConfirm([...selected.keys()]);
			// Only close once onConfirm has resolved without throwing.
			parent?.onClose?.();
		} catch (e) {
			// Keep the modal open so the selection isn't lost and the failure is visible.
			saveError = true;
			console.error('Entity picker confirm failed:', e);
		} finally {
			saving = false;
		}
	}

	hydrateSelection();
	load();
</script>

{#if $modalStore[0]}
	<div
		class="card bg-surface-50-950 shadow-xl w-[860px] max-w-[94vw] p-0 rounded-lg overflow-hidden"
	>
		<header class="flex items-center justify-between px-5 py-4 border-b border-surface-200-800">
			<div>
				<h3 class="text-lg font-medium">{title ?? safeTranslate('selectExisting')}</h3>
				{#if subtitle}
					<p class="text-sm text-surface-600-400">{subtitle}</p>
				{/if}
			</div>
			<button type="button" aria-label={m.close()} class="p-1" onclick={parent.onClose}>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</header>

		<div class="flex items-center gap-2 px-5 pt-4 pb-2">
			<div class="relative flex-1">
				<i
					class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"
				></i>
				<input
					type="text"
					class="input pl-9"
					placeholder={safeTranslate('search')}
					oninput={(e) => onSearch(e.currentTarget.value)}
				/>
			</div>
			<button
				type="button"
				class="btn preset-tonal flex items-center gap-2"
				onclick={() => (mode = mode === 'list' ? 'table' : 'list')}
			>
				<i class="fa-solid {mode === 'list' ? 'fa-table' : 'fa-list'}"></i>
				{mode === 'list' ? safeTranslate('browse') : safeTranslate('list')}
			</button>
			{#if activeField}
				<label class="flex items-center gap-2 text-sm text-surface-600-400 whitespace-nowrap">
					<input
						type="checkbox"
						class="checkbox"
						checked={includeInactive}
						onchange={toggleInactive}
					/>
					{safeTranslate('includeInactive')}
				</label>
			{/if}
		</div>

		<div class="flex items-center px-5 pb-1 min-h-[28px]">
			{#if rows.length > 0}
				<label class="flex items-center gap-2 text-sm text-surface-600-400 cursor-pointer">
					<input
						type="checkbox"
						class="checkbox"
						checked={pageAllSelected}
						onchange={toggleSelectAllPage}
					/>
					{safeTranslate('selectAll')}
				</label>
			{/if}
		</div>

		<div class="h-[520px] max-h-[62vh] overflow-y-auto px-3">
			{#if mode === 'list'}
				{#if loading}
					<div class="flex items-center justify-center h-full text-surface-500">
						<i class="fa-solid fa-circle-notch fa-spin"></i>
					</div>
				{:else if loadError}
					<div class="flex items-center justify-center h-full text-error-500 text-sm">
						<i class="fa-solid fa-triangle-exclamation mr-2"></i>{safeTranslate('error')}
					</div>
				{:else if rows.length === 0}
					<div class="flex items-center justify-center h-full text-surface-500 text-sm">
						{safeTranslate('noResults')}
					</div>
				{:else}
					{#each rows as row}
						<button
							type="button"
							class="w-full flex items-center gap-3 px-2 py-2 rounded text-left hover:bg-surface-100-900 {selected.has(
								row.id
							)
								? 'bg-primary-50-950'
								: ''}"
							onclick={() => toggle(row)}
						>
							<i
								class="fa-{selected.has(row.id) ? 'solid' : 'regular'} fa-square{selected.has(
									row.id
								)
									? '-check'
									: ''} text-lg {selected.has(row.id) ? 'text-primary-500' : 'text-surface-400'}"
							></i>
							<span
								class="w-8 h-8 rounded-full bg-primary-100-900 text-primary-700-300 flex items-center justify-center text-xs font-medium shrink-0"
								>{initials(row)}</span
							>
							<span class="flex-1 min-w-0 flex items-baseline gap-2">
								<span class="truncate max-w-[45%]">{label(row)}</span>
								{#if secondaryField && row[secondaryField] && row[secondaryField] !== label(row)}
									<span class="truncate text-surface-600-400">({row[secondaryField]})</span>
								{/if}
								{#if activeField && row[activeField] === false}
									<span
										class="shrink-0 text-xs px-2 rounded-full bg-surface-200-800 text-surface-600-400"
										>{safeTranslate('inactive')}</span
									>
								{/if}
							</span>
						</button>
					{/each}
				{/if}
			{:else}
				<table class="w-full text-sm">
					<thead class="sticky top-0 bg-surface-50-950">
						<tr class="text-left text-surface-600-400">
							<th class="w-6 py-1 pl-2"></th>
							{#each columns as col}
								<th class="py-1 pl-3 pr-3 font-medium">
									{#if col.sortable !== false}
										<button
											type="button"
											class="flex items-center gap-1 p-0 hover:text-primary-500"
											onclick={() => toggleSort(col.key)}
										>
											{safeTranslate(col.label)}
											<i
												class="fa-solid {sortIcon(col.key)} text-xs {ordering.replace('-', '') ===
												col.key
													? 'text-primary-500'
													: 'text-surface-400'}"
											></i>
										</button>
									{:else}
										{safeTranslate(col.label)}
									{/if}
								</th>
							{/each}
						</tr>
						<tr class="border-b border-surface-200-800">
							<th class="w-6 pb-2 pl-2"></th>
							{#each columns as col}
								<th class="pb-2 pr-3 font-normal">
									{#if col.filter}
										<input
											type="text"
											class="input text-sm h-8 w-full font-normal"
											placeholder={safeTranslate(col.label)}
											value={columnFilters[col.key] ?? ''}
											oninput={(e) => onColumnFilter(col.key, e.currentTarget.value)}
										/>
									{/if}
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#if loading}
							<tr>
								<td colspan={columns.length + 1} class="text-center py-16 text-surface-500">
									<i class="fa-solid fa-circle-notch fa-spin"></i>
								</td>
							</tr>
						{:else if loadError}
							<tr>
								<td colspan={columns.length + 1} class="text-center py-16 text-error-500 text-sm">
									<i class="fa-solid fa-triangle-exclamation mr-2"></i>{safeTranslate('error')}
								</td>
							</tr>
						{:else if rows.length === 0}
							<tr>
								<td colspan={columns.length + 1} class="text-center py-16 text-surface-500 text-sm">
									{safeTranslate('noResults')}
								</td>
							</tr>
						{:else}
							{#each rows as row}
								<tr
									tabindex="0"
									role="button"
									aria-pressed={selected.has(row.id)}
									class="cursor-pointer hover:bg-surface-100-900 {selected.has(row.id)
										? 'bg-primary-50-950'
										: ''}"
									onclick={() => toggle(row)}
									onkeydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											toggle(row);
										}
									}}
								>
									<td class="w-6 py-2 pl-2">
										<i
											class="fa-{selected.has(row.id) ? 'solid' : 'regular'} fa-square{selected.has(
												row.id
											)
												? '-check'
												: ''} {selected.has(row.id) ? 'text-primary-500' : 'text-surface-400'}"
										></i>
									</td>
									{#each columns as col}
										<td class="py-2 pl-3 pr-3 truncate">{row[col.key] ?? ''}</td>
									{/each}
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			{/if}
		</div>

		<div
			class="flex items-center justify-between px-5 py-2 border-y border-surface-200-800 text-sm text-surface-600-400"
		>
			<span class="flex items-center gap-3">
				<span>
					{count === 0 ? '0' : `${offset + 1}–${pageEnd}`}
					{safeTranslate('of')}
					{count.toLocaleString()}
				</span>
				<label class="flex items-center gap-2">
					{safeTranslate('show')}
					<select
						class="select select-sm h-8 w-auto py-0"
						value={pageSize}
						onchange={(e) => setPageSize(Number(e.currentTarget.value))}
					>
						{#each PAGE_SIZE_OPTIONS as opt}
							<option value={opt}>{opt}</option>
						{/each}
					</select>
					{safeTranslate('entries')}
				</label>
			</span>
			<span class="flex items-center gap-1">
				<button
					type="button"
					aria-label={safeTranslate('previous')}
					class="btn-icon btn-icon-sm"
					disabled={!hasPrev}
					onclick={prev}
				>
					<i class="fa-solid fa-chevron-left"></i>
				</button>
				<button
					type="button"
					aria-label={safeTranslate('next')}
					class="btn-icon btn-icon-sm"
					disabled={!hasNext}
					onclick={next}
				>
					<i class="fa-solid fa-chevron-right"></i>
				</button>
			</span>
		</div>

		<div class="px-5 py-3">
			<div class="flex items-center justify-between mb-1">
				<span class="text-sm text-surface-600-400"
					>{safeTranslate('selected')} ({selected.size})</span
				>
			</div>
			<div class="flex flex-wrap content-start gap-2 h-[60px] overflow-y-auto">
				{#if selected.size === 0}
					<span class="text-xs text-surface-500 py-1">{safeTranslate('nothingSelected')}</span>
				{:else}
					{#each [...selected.values()] as row}
						<span
							class="inline-flex items-center gap-2 text-xs pl-3 pr-2 py-1 rounded-full bg-surface-100-900 border border-surface-200-800"
						>
							<span class="max-w-[200px] truncate" title={label(row)}>{label(row)}</span>
							<button
								type="button"
								aria-label={m.remove()}
								class="shrink-0"
								onclick={() => selected.delete(row.id)}
							>
								<i class="fa-solid fa-xmark text-surface-500"></i>
							</button>
						</span>
					{/each}
				{/if}
			</div>
		</div>

		<footer class="flex items-center justify-end gap-3 px-5 py-3 border-t border-surface-200-800">
			{#if saveError}
				<span class="mr-auto text-sm text-error-500">
					<i class="fa-solid fa-triangle-exclamation mr-1"></i>{safeTranslate('error')}
				</span>
			{/if}
			<button type="button" class="btn preset-tonal" onclick={parent.onClose}>{m.cancel()}</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				disabled={saving || selected.size === 0}
				onclick={confirm}
			>
				{confirmLabel ?? m.save()}
			</button>
		</footer>
	</div>
{/if}
