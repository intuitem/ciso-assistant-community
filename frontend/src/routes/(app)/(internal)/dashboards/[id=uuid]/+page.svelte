<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	const dashboard = $derived(data.data);
</script>

<DetailView {data} {form}>
	{#snippet actions()}
		<a href="/dashboards/{dashboard.id}/view" class="btn preset-filled-success-500">
			<i class="fa-solid fa-chart-line"></i>
			{m.viewDashboard()}
		</a>
		<a href="/dashboards/{dashboard.id}/layout" class="btn preset-filled-warning-500">
			<i class="fa-solid fa-grip"></i>
			{m.editLayout()}
		</a>
	{/snippet}
</DetailView>
