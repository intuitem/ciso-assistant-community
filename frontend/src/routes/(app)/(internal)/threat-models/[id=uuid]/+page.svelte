<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet actions()}
		<Anchor
			breadcrumbAction="push"
			href={`${page.url.pathname}/select`}
			class="btn preset-tonal-secondary h-fit"
		>
			<i class="fa-solid fa-table-cells mr-2"></i>
			{m.selectTechniques()}
		</Anchor>
		<Anchor
			breadcrumbAction="push"
			href={`${page.url.pathname}/graph`}
			class="btn preset-filled-secondary-500 h-fit"
		>
			<i class="fa-solid fa-diagram-project mr-2"></i>
			{m.graph()}
		</Anchor>
	{/snippet}
</DetailView>
