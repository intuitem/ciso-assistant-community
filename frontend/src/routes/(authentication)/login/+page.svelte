<script lang="ts">
	import type { ActionData, PageData } from './$types';
	import Logo from '$lib/components/Logo/Logo.svelte';
	import Greetings from './Greetings.svelte';
	import FormCard from './FormCard.svelte';
	import MfaAuthenticateModal from './mfa/components/MFAAuthenticateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '@skeletonlabs/skeleton';

	export let data: PageData;
	export let form: ActionData;

	const modalStore: ModalStore = getModalStore();

	function modalMFAAuthenticate(): void {
		const modalComponent: ModalComponent = {
			ref: MfaAuthenticateModal,
			props: {
				_form: data.mfaAuthenticateForm,
				formAction: '?/mfaAuthenticate'
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: '_mfaAuthenticateTitle',
			body: '_mfaAuthenticateMessage'
		};
		modalStore.trigger(modal);
	}

	$: form && form.mfaFlow ? modalMFAAuthenticate() : null;
</script>

<div class="relative h-screen w-screen bg-slate-200">
	<div class="absolute top-5 left-5">
		<div class="flex flex-row max-w-48 space-x-4 pb-3">
			<Logo />
		</div>
	</div>
	<div class="absolute top-1/2 left-1/2 w-full transform -translate-x-1/2 -translate-y-1/2">
		<div class="flex flex-row w-full pr-8">
			<Greetings />
			<div class="flex justify-center pr-5 items-center space-y-4 w-2/5">
				<FormCard {data} />
			</div>
		</div>
	</div>
</div>
