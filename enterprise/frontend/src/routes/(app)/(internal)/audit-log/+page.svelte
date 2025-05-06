<script lang="ts">
	import type { PageData } from './$types';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	export let data: PageData;
</script>

<main class="bg-white card p-4">
  <ModelTable
    source={
    {head: {actor: 'actor', changes: 'changes_text', timestamp: 'timestamp'}, body: [], meta: []}
    }
    URLModel='audit-log'
    baseEndpoint="/audit-log"
    fields={['actor','changes_text', 'timestamp']}
  />
</main>
