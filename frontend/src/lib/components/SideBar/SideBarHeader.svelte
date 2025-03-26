<script lang="ts">
	import Logo from '$lib/components/Logo/Logo.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import * as m from '$paraglide/messages';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { PageData, ActionData } from './$types';
	import QuickStartModal from './QuickStart/QuickStartModal.svelte';

	export let data: PageData;
	export let form: ActionData;

	const modalStore: ModalStore = getModalStore();

	function modalQuickStart(): void {
		let modalComponent: ModalComponent = {
			ref: QuickStartModal,
			props: {}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.quickStart()
		};
		modalStore.trigger(modal);
	}
</script>

<header>
	<div
		class="flex flex-row space-x-4 border-b pb-3 items-center justify-center"
		on:click={modalQuickStart}
	>
		<Logo />
	</div>
</header>
