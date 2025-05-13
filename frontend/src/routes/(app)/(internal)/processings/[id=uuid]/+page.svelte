<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/stores';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import * as m from '$paraglide/messages';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	<!-- <div slot="actions" class="flex flex-col space-y-2"> -->
	<!-- 	<Anchor -->
	<!-- 		href={`${$page.url.pathname}/summary`} -->
	<!-- 		class="btn variant-filled-primary h-fit" -->
	<!-- 		breadcrumbAction="push"><i class="fa-solid fa-heart-pulse mr-2" />{m.summary()}</Anchor -->
	<!-- 	> -->
	<!-- </div> -->
	<!---->
	<!-- <div slot="widgets" class="h-full flex flex-col space-y-4 bg-slate-100"></div> -->
</DetailView>
