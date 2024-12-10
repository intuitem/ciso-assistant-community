<script lang="ts">
	import * as m from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import Tile from './Tile.svelte';
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import { breadcrumbObject } from '$lib/utils/stores';

	export let data: PageData;

	$: breadcrumbObject.set(data.data);

	const dummydata = {
		ws1: [
			{
				title: safeTranslate(m.ebiosWs1_1()),
				status: 'done',
				href: `${$page.url.pathname}/workshop-one/ebios-rm-study?activity=one&next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs1_2()),
				status: 'done',
				href: `${$page.url.pathname}/workshop-one/ebios-rm-study?activity=two&next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs1_3()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-one/feared-events?next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs1_4()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-one/baseline?next=${$page.url.pathname}`
			}
		],
		ws2: [
			{
				title: safeTranslate(m.ebiosWs2_1()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-two/ro-to?next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs2_2()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-two/ro-to?next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs2_3()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-two/ro-to?next=${$page.url.pathname}`
			}
		],
		ws3: [
			{
				title: safeTranslate(m.ebiosWs3_1()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-three/ecosystem?next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs3_2()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-three/strategic-scenarios?next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs3_3()),
				status: 'done',
				href: `${$page.url.pathname}/workshop-three/ecosystem?next=${$page.url.pathname}`
			}
		],
		ws4: [
			{
				title: safeTranslate(m.ebiosWs4_1()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-four/operational-scenario?next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs4_2()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-four/operational-scenario?next=${$page.url.pathname}`
			}
		],
		ws5: [
			{ title: safeTranslate(m.ebiosWs5_1()), status: 'done', href: '#' },
			{ title: safeTranslate(m.ebiosWs5_2()), status: 'done', href: '#' },
			{ title: safeTranslate(m.ebiosWs5_3()), status: 'to_do', href: '#' },
			{ title: safeTranslate(m.ebiosWs5_4()), status: 'to_do', href: '#' },
			{ title: safeTranslate(m.ebiosWs5_5()), status: 'done', href: '#' }
		]
	};
</script>

<div class="h-full w-full p-8">
	<div
		class="card bg-white shadow-lg w-full h-full grid xl:grid-cols-3 lg:grid-cols-2 md:grid-cols-1 gap-8 p-8"
	>
		<Tile title={m.ebiosWs1()} accent_color="bg-pink-600" status="to_do" meta={dummydata.ws1} />
		<Tile title={m.ebiosWs2()} accent_color="bg-fuchsia-900" status="to_do" meta={dummydata.ws2} />
		<Tile title={m.ebiosWs3()} accent_color="bg-teal-500" status="to_do" meta={dummydata.ws3} />
		<Tile title={m.ebiosWs4()} accent_color="bg-yellow-600" status="to_do" meta={dummydata.ws4} />
		<Tile title={m.ebiosWs5()} accent_color="bg-red-500" status="to_do" meta={dummydata.ws5} />
		<Tile title={m.summary()} accent_color="bg-purple-800" status="to_do" />
	</div>
</div>
