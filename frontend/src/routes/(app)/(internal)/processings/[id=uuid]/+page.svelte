<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/stores';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import * as m from '$paraglide/messages';
	import { IconDiamond } from '@tabler/icons-svelte';
	export let data: PageData;
</script>

<DetailView {data}>
	<div slot="actions" class="flex flex-col space-y-2">
		<Anchor
			href={`${$page.url.pathname}/summary`}
			class="btn variant-filled-primary h-fit"
			breadcrumbAction="push"><i class="fa-solid fa-heart-pulse mr-2" />{m.summary()}</Anchor
		>
	</div>

	<div slot="widgets" class="h-full flex flex-col space-y-4 bg-slate-100">
		<!-- <div class="grid grid-cols-2 p-4 gap-4"> -->
		<!-- 	<div class="bg-white rounded-xl min-h-40"> -->
		<!-- 		<IconDiamond size={48} stroke={1} /> 12 personal data -->
		<!-- 	</div> -->
		<!-- 	<div class="bg-white rounded-xl"> -->
		<!-- 		<IconDiamond size={48} stroke={1} /> 8 marked as sensitive -->
		<!-- 	</div> -->
		<!-- </div> -->
	</div>
</DetailView>
