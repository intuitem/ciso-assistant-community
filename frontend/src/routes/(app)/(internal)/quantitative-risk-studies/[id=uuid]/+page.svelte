<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<Anchor
				href={`${page.url.pathname}/action-plan`}
				class="btn preset-filled-primary-500 h-fit"
				breadcrumbAction="push"
			>
				<i class="fa-solid fa-heart-pulse mr-2"></i>{m.actionPlan()}
			</Anchor>
			<Anchor
				href={`${page.url.pathname}/executive-summary`}
				class="btn preset-filled-secondary-500 h-fit"
				breadcrumbAction="push"
			>
				<i class="fa-solid fa-chart-line mr-2"></i>Executive Summary
			</Anchor>
		</div>
	{/snippet}
</DetailView>
