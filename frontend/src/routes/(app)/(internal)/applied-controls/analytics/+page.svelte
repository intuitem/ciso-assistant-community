<script lang="ts">
	import AppliedControlsAnalytics from '$lib/components/DataViz/AppliedControlsAnalytics.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="p-4 space-y-4">
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-3">
			<Anchor href={`${data.backUrl}${data.filterSearch}`} class="btn variant-ghost-surface">
				<i class="fa-solid fa-arrow-left mr-2" aria-hidden="true"></i>
				{safeTranslate(data.backLabel) || data.backLabel}
			</Anchor>
			<h1 class="text-2xl font-bold text-gray-900">{m.appliedControlsAnalytics()}</h1>
		</div>
		{#if data.hasFilters}
			<span
				class="text-xs px-2 py-1 rounded-full bg-violet-100 text-violet-700 border border-violet-200"
				title={m.analyticsFilteredHint()}
			>
				<i class="fa-solid fa-filter mr-1" aria-hidden="true"></i>{m.analyticsFilteredHint()}
			</span>
		{/if}
	</div>

	<AppliedControlsAnalytics analyticsData={data.analytics} />
</div>
