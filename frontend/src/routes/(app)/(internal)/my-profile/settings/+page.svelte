<script lang="ts">
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import ActivateTOTPModal from './mfa/components/ActivateTOTPModal.svelte';

	import * as m from '$paraglide/messages';

	export let data: PageData;

	const modalStore: ModalStore = getModalStore();

	function modalActivateTOTP(totp: Record<string, any>): void {
		const modalComponent: ModalComponent = {
			ref: ActivateTOTPModal,
			props: {
				_form: data.activateTOTPForm,
				formAction: '?/activateTOTP',
				totp
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: '_activateTOTPTitle',
			body: '_activateTOTPMessage'
		};
		modalStore.trigger(modal);
	}
</script>

<div class="card p-4 bg-white shadow-lg flow-root">
	<dl class="-my-3 divide-y divide-gray-100 text-sm">
		<div class="grid grid-cols-1 gap-1 py-3 sm:grid-cols-3 sm:gap-4">
			<dt class="font-medium text-gray-900">Authenticators</dt>
			<dd class="text-gray-700 sm:col-span-2">
				{#if data.authenticators.length > 0}
					{#each data.authenticators as authenticator}
						{authenticator.type}&nbsp;
					{/each}
				{:else}
					There are currently no authenticators associated with this account.
				{/if}
			</dd>
		</div>

		{#if data.authenticators.length < 1}
			<div class="grid grid-cols-1 gap-1 py-3 sm:grid-cols-3 sm:gap-4">
				<dt class="font-medium text-gray-900">TOTP</dt>
				<dd class="text-gray-700 sm:col-span-2">
					<button class="btn variant-ghost-secondary" on:click={(_) => modalActivateTOTP(data.totp)}
						>TOTP</button
					>
				</dd>
			</div>
		{/if}
	</dl>
</div>
