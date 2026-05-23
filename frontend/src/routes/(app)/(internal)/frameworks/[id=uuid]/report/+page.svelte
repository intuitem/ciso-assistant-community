<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import ReportView from './ReportView.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Initial title before the report payload resolves; ReportView refines it
	// to "{framework name} — {label}" once data is in.
	$pageTitle = m.frameworkReport();
</script>

{#await data.stream.report}
	<div class="flex items-center justify-center h-64">
		<LoadingSpinner />
	</div>
{:then report}
	<ReportView {report} />
{:catch err}
	<div class="card p-6 m-2 bg-white text-sm text-red-700">
		{err?.message ?? m.frameworkReport()}
	</div>
{/await}
