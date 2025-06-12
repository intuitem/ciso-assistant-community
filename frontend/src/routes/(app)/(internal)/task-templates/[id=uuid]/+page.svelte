<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView
	{data}
	displayModelTable={data.data.is_recurrent}
	exclude={data.data.is_recurrent
		? ['observation', 'evidences', 'status']
		: ['last_occurrence_status', 'next_occurrence']}
/>
