<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import type { PageData, ActionData } from './$types';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
</script>

{#if data.model.name === 'fearedevent'}
	<div class="flex items-center justify-between mb-4">
		<Anchor
			breadcrumbAction="push"
			href={`/ebios-rm/${data.data.ebios_rm_study.id}`}
			class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<p>{m.goBackToEbiosRmStudy()}</p>
		</Anchor>
	</div>
{/if}

<DetailView {data} />

{#if data.model.name == 'requirementmappingset' && data.data.frameworks_available}
	<div class="card my-4 p-4 bg-white">
		<span class="bg-purple-700 text-white px-2 py-1 rounded-sm text-sm font-semibold">new</span><a
			class="ml-2 hover:text-purple-700"
			href={`/experimental/mapping/${data.data.id}`}>{m.viewOnGraphExplorer()}</a
		>
	</div>
{/if}
