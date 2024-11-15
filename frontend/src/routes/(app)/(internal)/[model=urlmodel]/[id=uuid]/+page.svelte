<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData, ActionData } from './$types';
	import { goto } from '$app/navigation';
	import { getSecureRedirect } from '$lib/utils/helpers';

	export let data: PageData;
	export let form: ActionData;

	$: if (form && form.redirect) {
		goto(getSecureRedirect(form.redirect));
	}
</script>

<DetailView {data} />
{#if data.model.name == 'requirementmappingset'}
	<div class="card my-4 p-4 bg-white">
		<span class="bg-purple-700 text-white px-2 py-1 rounded text-sm font-semibold">beta</span><a
			class="ml-2 hover:text-purple-700"
			href={`/experimental/mapping/${data.data.id}`}>View on graph explorer</a
		>
	</div>
{/if}
