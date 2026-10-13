<script lang="ts">
	import { formatDate } from '$lib/utils/datetime';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const overview = $derived(data.overview);

	// Most urgent first: each band links to the processings it counts.
	const bands = $derived([
		{
			key: 'required_without_dpia',
			label: m.dpiaRequiredNoDpiaYet(),
			count: overview.required_without_dpia,
			color: 'var(--color-error-500)',
			href: '/processings?dpia_required=true'
		},
		{
			key: 'required_dpia_in_progress',
			label: m.dpiaRequiredDpiaStarted(),
			count: overview.required_dpia_in_progress,
			color: 'var(--color-warning-500)',
			href: '/dpias'
		},
		{
			key: 'required_dpia_done',
			label: m.dpiaRequiredDpiaDone(),
			count: overview.required_dpia_done,
			color: 'var(--color-primary-500)',
			href: '/dpias'
		},
		{
			key: 'not_required',
			label: m.dpiaRequiredNo(),
			count: overview.not_required,
			color: 'var(--color-success-500)',
			href: '/processings?dpia_required=false'
		},
		{
			key: 'not_assessed',
			label: m.dpiaNotScreenedYet(),
			count: overview.not_assessed,
			color: 'var(--color-surface-400)',
			// No filter isolates "never set" from "set to no".
			href: null
		}
	]);

	function share(count: number): number {
		return overview.total ? Math.round((count / overview.total) * 100) : 0;
	}
</script>

<div class="bg-surface-50-950 shadow-sm flex flex-col">
	<header
		class="flex flex-wrap items-start justify-between gap-4 px-6 pt-6 pb-5 border-b border-surface-200-800"
	>
		<div class="flex flex-col gap-1 max-w-2xl">
			<h1 class="text-2xl font-semibold tracking-tight text-surface-950-50">
				<i class="fa-solid fa-scale-balanced mr-2 text-surface-500"></i>{m.dpiaStatusOverview()}
			</h1>
			<p class="text-sm text-surface-600-400">{m.dpiaOverviewDescription()}</p>
		</div>
		<a
			href="/processings"
			class="text-sm text-primary-800-200 hover:text-primary-500 whitespace-nowrap pt-1"
		>
			<i class="fa-solid fa-arrow-left mr-2"></i>{m.backToTable()}
		</a>
	</header>

	<div class="grid gap-8 p-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
		<div class="flex flex-col gap-6">
			<section class="flex flex-col gap-3" aria-label={m.dpiaStatusOverview()}>
				<p class="text-xl font-semibold tabular-nums text-surface-950-50">
					{m.processingsCountLabel({ count: overview.total })}
				</p>
				<div
					class="flex h-3 w-full overflow-hidden rounded-full bg-surface-200-800"
					aria-hidden="true"
				>
					{#each bands.filter((b) => b.count > 0) as band (band.key)}
						<span
							class="h-full first:rounded-l-full last:rounded-r-full"
							style="flex-grow: {band.count}; background: {band.color}"
							title="{band.label}: {band.count}"
						></span>
					{/each}
				</div>
				<ul class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" data-testid="dpia-overview-bands">
					{#each bands as band (band.key)}
						<li>
							<svelte:element
								this={band.href ? 'a' : 'div'}
								href={band.href}
								class="card flex flex-col gap-1 border border-surface-200-800 border-l-4 bg-surface-50-950 p-3 {band.href
									? 'hover:shadow-md'
									: ''}"
								style="border-left-color: {band.color}"
							>
								<span class="text-2xl font-semibold tabular-nums text-surface-950-50"
									>{band.count}</span
								>
								<span class="text-sm text-surface-700-300">{band.label}</span>
								<span class="text-xs tabular-nums text-surface-500">{share(band.count)}%</span>
							</svelte:element>
						</li>
					{/each}
				</ul>
				{#if overview.awaiting_review}
					<a
						class="text-sm text-primary-800-200 hover:text-primary-500"
						href="/quick-form-responses?status=submitted&status=in_review"
						data-testid="dpia-awaiting-review"
					>
						<i class="fa-solid fa-hourglass-half mr-1.5 text-xs"
						></i>{m.dpiaScreeningsAwaitingReview({
							count: overview.awaiting_review
						})}
						<i class="fa-solid fa-arrow-right ml-1 text-xs"></i>
					</a>
				{/if}
			</section>

			<section class="flex flex-col gap-3" data-testid="dpia-gaps">
				<h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-surface-500">
					{m.dpiaRequiredNoDpiaYet()}
				</h2>
				{#if overview.gaps.length === 0}
					<p class="text-sm text-surface-500">{m.dpiaNoGaps()}</p>
				{:else}
					<ul
						class="flex flex-col divide-y divide-surface-200-800 rounded-xl border border-surface-200-800"
					>
						{#each overview.gaps as gap (gap.id)}
							<li class="flex flex-wrap items-center gap-3 px-4 py-2.5">
								<a class="anchor font-medium" href={`/processings/${gap.id}`}
									>{gap.ref_id ? `${gap.ref_id} - ` : ''}{gap.name}</a
								>
								<span class="text-xs text-surface-500">{gap.folder}</span>
								{#if gap.set_at}
									<span class="ml-auto text-xs text-surface-500"
										>{m.dpiaRequiredSince({
											date: formatDate(new Date(gap.set_at), false, getLocale())
										})}</span
									>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</section>
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
