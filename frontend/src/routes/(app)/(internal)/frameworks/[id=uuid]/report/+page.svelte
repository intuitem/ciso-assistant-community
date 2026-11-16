<script lang="ts">
	import { pageTitle } from '#lib/utils/stores.js';
	import { m } from '#paraglide/messages.js';
	import LoadingSpinner from '#lib/components/utils/LoadingSpinner.svelte';
	import ReportView from './ReportView.svelte';
	import type { PageData } from './$types';
	import type { ComponentProps } from 'svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Initial title before the report payload resolves; ReportView refines it
	// to "{framework name} — {label}" once data is in.
	$pageTitle = m.frameworkReport();

	// The previous report stays mounted while a reload streams in, so filters survive.
	let report = $state<ComponentProps<typeof ReportView>['report'] | null>(null);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	$effect(() => {
		const pending = data.stream.report;
		loading = true;
		pending
			.then((value) => {
				if (pending !== data.stream.report) return;
				report = value;
				loadError = null;
			})
			.catch((err) => {
				if (pending === data.stream.report) loadError = err?.message ?? m.frameworkReport();
			})
			.finally(() => {
				if (pending === data.stream.report) loading = false;
			});
	});
</script>

{#if loadError}
	<div class="card p-6 m-2 bg-surface-50-950 text-sm text-red-700">{loadError}</div>
{:else if report}
	<div class="relative" aria-busy={loading}>
		{#key report.framework?.id}
			<ReportView {report} />
		{/key}
		{#if loading}
			<div class="absolute top-2 right-2"><LoadingSpinner /></div>
		{/if}
	</div>
{:else}
	<div class="flex items-center justify-center h-64">
		<LoadingSpinner />
	</div>
{/if}
