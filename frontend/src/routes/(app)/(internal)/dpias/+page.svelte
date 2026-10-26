<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { formatDate } from '#lib/utils/datetime.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const toastStore = getToastStore();
	const overview = $derived(data.overview);
	const PAGE = 50;

	// Most urgent first; each band filters the table below.
	const bands = $derived([
		{
			key: 'required_without_dpia',
			label: m.dpiaRequiredNoDpiaYet(),
			color: 'var(--color-error-500)'
		},
		{
			key: 'required_dpia_in_progress',
			label: m.dpiaRequiredDpiaStarted(),
			color: 'var(--color-warning-500)'
		},
		{
			key: 'required_dpia_done',
			label: m.dpiaRequiredDpiaDone(),
			color: 'var(--color-primary-500)'
		},
		{ key: 'not_required', label: m.dpiaRequiredNo(), color: 'var(--color-success-500)' },
		{ key: 'not_assessed', label: m.dpiaNotScreenedYet(), color: 'var(--color-surface-400)' }
	]);
	const bandOf = $derived(Object.fromEntries(bands.map((b) => [b.key, b])));

	const filter = $derived(page.url.searchParams.get('state') ?? '');
	const search = $derived(page.url.searchParams.get('search') ?? '');
	const offset = $derived(Number(page.url.searchParams.get('offset')) || 0);

	function share(count: number): number {
		return overview.total ? Math.round((count / overview.total) * 100) : 0;
	}

	// The page's URL with these params changed; a new filter or search starts at the top.
	function hrefWith(changes: Record<string, string | number | null>): string {
		const params = new URLSearchParams(page.url.search);
		if (!('offset' in changes)) params.delete('offset');
		for (const [key, value] of Object.entries(changes)) {
			if (value === null || value === '' || value === 0) params.delete(key);
			else params.set(key, String(value));
		}
		const query = params.toString();
		return query ? `?${query}` : page.url.pathname;
	}

	function onSearch(event: SubmitEvent) {
		event.preventDefault();
		const value = new FormData(event.currentTarget as HTMLFormElement).get('search');
		goto(hrefWith({ search: String(value ?? '').trim() }), { reset: false });
	}

	// One start at a time: a double click must not open two drafts.
	let starting: string | null = $state(null);

	// Starts the screening or the DPIA of a processing through the one form the
	// viewer may use; with several, the processing's card offers the choice.
	async function start(
		processingId: string,
		target: 'processing.dpia_required' | 'processing.dpia'
	) {
		if (starting) return;
		starting = processingId;
		const base = `/processings/${processingId}/dpia-screening`;
		try {
			const options = await fetch(`${base}?target=${target}`).then((res) =>
				res.ok ? res.json() : []
			);
			if (!Array.isArray(options) || options.length !== 1) {
				if (Array.isArray(options) && options.length > 1) {
					await goto(`/processings/${processingId}`);
				} else {
					toastStore.trigger({
						message: m.noDpiaScreeningForm(),
						background: 'preset-filled-warning-500'
					});
				}
				return;
			}
			const res = await fetch(base, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ kind: options[0].kind, id: options[0].id })
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok || !body.redirect) {
				toastStore.trigger({
					message: body.error ? safeTranslate(body.error) : m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			await goto(body.redirect);
		} catch {
			toastStore.trigger({ message: m.anErrorOccurred(), background: 'preset-filled-error-500' });
		} finally {
			starting = null;
		}
	}
</script>

<div class="bg-surface-50-950 shadow-sm flex flex-col">
	<header class="flex flex-col gap-1 px-6 pt-6 pb-5 border-b border-surface-200-800">
		<h1 class="text-2xl font-semibold tracking-tight text-surface-950-50">
			<i class="fa-solid fa-scale-balanced mr-2 text-surface-500"></i>{m.dpias()}
		</h1>
		<p class="text-sm text-surface-600-400 max-w-2xl">{m.dpiaOverviewDescription()}</p>
	</header>

	<div class="grid gap-8 p-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
		<div class="flex min-w-0 flex-col gap-5">
			<section class="flex flex-col gap-3" aria-label={m.dpias()}>
				<div
					class="flex h-2.5 w-full overflow-hidden rounded-full bg-surface-200-800"
					aria-hidden="true"
				>
					{#each bands.filter((b) => overview[b.key] > 0) as band (band.key)}
						<span
							class="h-full"
							style="flex-grow: {overview[band.key]}; background: {band.color}"
							title="{band.label}: {overview[band.key]}"
						></span>
					{/each}
				</div>
				<nav class="flex flex-wrap gap-2" data-testid="dpia-overview-bands">
					<a
						href={hrefWith({ state: null })}
						class="chip {filter === '' ? 'preset-filled-surface-950-50' : 'preset-tonal-surface'}"
						aria-current={filter === '' ? 'page' : undefined}
						>{m.all()} <span class="tabular-nums opacity-70">{overview.total}</span></a
					>
					{#each bands as band (band.key)}
						<a
							href={hrefWith({ state: band.key })}
							class="chip gap-1.5 {filter === band.key
								? 'preset-filled-surface-950-50'
								: 'preset-tonal-surface'}"
							aria-current={filter === band.key ? 'page' : undefined}
							title="{share(overview[band.key])}%"
						>
							<span class="size-2 rounded-full" style="background: {band.color}"></span>
							{band.label}
							<span class="tabular-nums opacity-70">{overview[band.key]}</span>
						</a>
					{/each}
					{#if overview.awaiting_review}
						<a
							href={hrefWith({ state: 'awaiting_review' })}
							class="chip gap-1.5 {filter === 'awaiting_review'
								? 'preset-filled-surface-950-50'
								: 'preset-tonal-warning'}"
							aria-current={filter === 'awaiting_review' ? 'page' : undefined}
							data-testid="dpia-awaiting-review"
						>
							<i class="fa-solid fa-hourglass-half text-xs"></i>
							{m.dpiaScreeningsAwaitingReview({ count: overview.awaiting_review })}
						</a>
					{/if}
				</nav>
			</section>

			<form class="flex gap-2" onsubmit={onSearch} role="search">
				<input
					class="input max-w-sm"
					type="search"
					name="search"
					value={search}
					oninput={(e) => {
						// The field's clear button resets the list too.
						if (search && !e.currentTarget.value)
							goto(hrefWith({ search: null }), { reset: false });
					}}
					placeholder={m.searchPlaceholder()}
					aria-label={m.search()}
				/>
			</form>

			<section
				class="overflow-x-auto rounded-xl border border-surface-200-800"
				data-testid="dpia-rows"
			>
				{#if overview.rows.length === 0}
					<p class="p-4 text-sm text-surface-500">
						{filter === 'required_without_dpia' && !search ? m.dpiaNoGaps() : m.noResultFound()}
					</p>
				{:else}
					<table class="table text-sm">
						<thead>
							<tr>
								<th>{m.processing()}</th>
								<th>{m.domain()}</th>
								<th>{m.status()}</th>
								<th>{m.dpia()}</th>
								<th>{m.since()}</th>
								<th class="text-right">{m.action()}</th>
							</tr>
						</thead>
						<tbody>
							{#each overview.rows as row (row.id)}
								{@const band = bandOf[row.state]}
								<tr>
									<td>
										<a class="anchor font-medium" href={`/processings/${row.id}`}
											>{row.ref_id ? `${row.ref_id} - ` : ''}{row.name}</a
										>
									</td>
									<td class="text-surface-600-400">{row.folder}</td>
									<td>
										<span class="inline-flex items-center gap-1.5 whitespace-nowrap">
											<span class="size-2 rounded-full" style="background: {band.color}"></span>
											{band.label}
										</span>
									</td>
									<td>
										{#if row.dpia}
											<a
												class="anchor whitespace-nowrap"
												href={`/quick-form-responses/${row.dpia.id}`}>{row.dpia.ref_id}</a
											>
											<span class="badge preset-tonal-surface text-xs"
												>{safeTranslate(row.dpia.resolution || row.dpia.status)}</span
											>
										{:else}
											<span class="text-surface-400">—</span>
										{/if}
									</td>
									<td class="whitespace-nowrap text-surface-600-400">
										{row.set_at ? formatDate(new Date(row.set_at), false, getLocale()) : '—'}
									</td>
									<td class="text-right whitespace-nowrap">
										{#if row.pending_screening}
											<a
												class="btn btn-sm preset-tonal-warning"
												href={`/quick-form-responses/${row.pending_screening.id}`}
												><i class="fa-solid fa-hourglass-half mr-1"></i>{m.review()}</a
											>
										{:else if row.state === 'required_without_dpia'}
											<button
												type="button"
												class="btn btn-sm preset-filled-primary-500"
												disabled={starting !== null}
												onclick={() => start(row.id, 'processing.dpia')}
												data-testid="start-dpia-button"
												><i class="fa-solid fa-file-shield mr-1"></i>{m.startDpia()}</button
											>
										{:else if row.state === 'required_dpia_in_progress' && row.dpia}
											<a
												class="btn btn-sm preset-tonal-primary"
												href={`/quick-form-responses/${row.dpia.id}`}>{m.continue()}</a
											>
										{:else if row.state === 'not_assessed'}
											<button
												type="button"
												class="btn btn-sm preset-tonal-primary"
												disabled={starting !== null}
												onclick={() => start(row.id, 'processing.dpia_required')}
												data-testid="dpia-screening-button"
												><i class="fa-solid fa-clipboard-check mr-1"
												></i>{m.dpiaScreeningStart()}</button
											>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			</section>

			{#if overview.rows_count > PAGE}
				<div class="flex items-center justify-end gap-3 text-sm text-surface-600-400">
					<span class="tabular-nums"
						>{offset + 1}–{Math.min(offset + PAGE, overview.rows_count)} / {overview.rows_count}</span
					>
					<a
						class="btn btn-sm preset-tonal {offset === 0 ? 'pointer-events-none opacity-50' : ''}"
						href={hrefWith({ offset: Math.max(offset - PAGE, 0) })}
						aria-disabled={offset === 0}>{m.previous()}</a
					>
					<a
						class="btn btn-sm preset-tonal {offset + PAGE >= overview.rows_count
							? 'pointer-events-none opacity-50'
							: ''}"
						href={hrefWith({ offset: offset + PAGE })}
						aria-disabled={offset + PAGE >= overview.rows_count}>{m.next()}</a
					>
				</div>
			{/if}
		</div>

		<aside class="flex flex-col gap-5">
			<section
				class="card bg-surface-100-900/60 p-4 flex flex-col gap-3"
				data-testid="dpia-screening-forms"
			>
				<h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-surface-500">
					{m.dpiaScreeningForms()}
				</h2>
				{#if (data.forms ?? []).length === 0}
					<p class="text-sm text-surface-500">{m.noDpiaScreeningForm()}</p>
					<a class="anchor text-sm" href="/libraries?object_type=quick_forms">{m.libraries()}</a>
				{:else}
					<ul class="flex flex-col gap-2.5 text-sm">
						{#each data.forms as quickForm (quickForm.id)}
							<li class="flex items-start gap-2.5">
								{#if quickForm.problems.length}
									<i
										class="fa-solid fa-triangle-exclamation mt-0.5 text-warning-600-400"
										aria-hidden="true"
									></i>
								{:else}
									<i class="fa-solid fa-circle-check mt-0.5 text-success-500" aria-hidden="true"
									></i>
								{/if}
								<div class="flex min-w-0 flex-col">
									<a class="anchor font-medium" href={`/quick-forms/${quickForm.id}`}
										>{quickForm.name}</a
									>
									{#if quickForm.library}
										<span class="truncate text-xs text-surface-500">{quickForm.library}</span>
									{/if}
									{#if quickForm.problems.length}
										<span class="text-xs text-warning-700 dark:text-warning-400">
											{quickForm.problems.map((p: string) => safeTranslate(p)).join(', ')}
										</span>
									{/if}
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</section>
		</aside>
	</div>
</div>
