<script lang="ts">
	import * as m from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import Tile from './Tile.svelte';
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import { breadcrumbObject } from '$lib/utils/stores';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import MissingConstraintsModal from '$lib/components/Modals/MissingConstraintsModal.svelte';
	import { checkConstraints } from '$lib/utils/crud';
	const modalStore: ModalStore = getModalStore();

	export let data: PageData;

	$: breadcrumbObject.set(data.data);

	const riskAnalysisCreated: boolean = data.data.risk_assessments.length > 0;

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
			{
				title: safeTranslate(m.ebiosWs5_1()),
				status: riskAnalysisCreated ? 'done' : 'to_do',
				href: '#'
			},
			{
				title: safeTranslate(m.ebiosWs5_2()),
				status: 'done',
				href: `${$page.url.pathname}/workshop-five/risk-analyses?next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs5_3()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-five/risk-analyses?next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs5_4()),
				status: 'to_do',
				href: `${$page.url.pathname}/workshop-five/risk-analyses?next=${$page.url.pathname}`
			},
			{
				title: safeTranslate(m.ebiosWs5_5()),
				status: 'done',
				href: `${$page.url.pathname}/workshop-five/risk-analyses?next=${$page.url.pathname}`
			}
		]
	};

	function modalCreateForm(): void {
		let modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.createRiskAnalysisForm,
				model: data.model
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + data.model.localName)
		};
		if (
			checkConstraints(data.createRiskAnalysisForm.constraints, data.model.foreignKeys).length > 0
		) {
			modalComponent = {
				ref: MissingConstraintsModal
			};
			modal = {
				type: 'component',
				component: modalComponent,
				title: m.warning(),
				body: safeTranslate('add-' + data.model.localName).toLowerCase(),
				value: checkConstraints(data.createRiskAnalysisForm.constraints, data.model.foreignKeys)
			};
		}
		modalStore.trigger(modal);
	}
</script>

<div class="h-full w-full p-8">
	<div
		class="card bg-white shadow-lg w-full h-full grid xl:grid-cols-3 lg:grid-cols-2 md:grid-cols-1 gap-8 p-8"
	>
		<Tile title={m.ebiosWs1()} accent_color="bg-pink-600" status="to_do" meta={dummydata.ws1} />
		<Tile title={m.ebiosWs2()} accent_color="bg-fuchsia-900" status="to_do" meta={dummydata.ws2} />
		<Tile title={m.ebiosWs3()} accent_color="bg-teal-500" status="to_do" meta={dummydata.ws3} />
		<Tile title={m.ebiosWs4()} accent_color="bg-yellow-600" status="to_do" meta={dummydata.ws4} />
		<Tile
			title={m.ebiosWs5()}
			accent_color="bg-red-500"
			status="to_do"
			meta={dummydata.ws5}
			createRiskAnalysis={true}
		>
			<div slot="addRiskAnalysis">
				<button class="flex flex-col text-left hover:text-purple-800" on:click={modalCreateForm}>
					<span
						class="absolute flex items-center justify-center w-8 h-8 bg-gray-100 rounded-full -start-4 ring-4 ring-white"
					>
						<i class="fa-solid fa-clipboard-check"></i>
					</span>
					<h3 class="font-medium leading-tight">{m.activity()} 1</h3>
					<p class="text-sm">{safeTranslate(m.ebiosWs5_1())}</p>
				</button>
			</div>
		</Tile>
		<Tile title={m.summary()} accent_color="bg-purple-800" status="to_do" />
	</div>
</div>
