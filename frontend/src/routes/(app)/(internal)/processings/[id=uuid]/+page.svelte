<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import * as m from '$paraglide/messages';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}></DetailView>
