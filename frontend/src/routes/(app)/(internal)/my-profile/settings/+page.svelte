<script lang="ts">
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import ActivateTOTPModal from './mfa/components/ActivateTOTPModal.svelte';
	import { TabGroup, Tab } from '@skeletonlabs/skeleton';

	import * as m from '$paraglide/messages';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';

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
			title: m.activateTOTPTitle(),
			body: m.activateTOTPMessage()
		};
		modalStore.trigger(modal);
	}

	function modalConfirm(action: string): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				debug: false,
				formAction: action
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.confirmModalTitle(),
			body: `${m.confirmModalMessage()}?`
		};
		modalStore.trigger(modal);
	}

	let tabSet = 0;
</script>

<TabGroup active="bg-primary-100 text-primary-800 border-b border-primary-800">
	<Tab bind:group={tabSet} name="ssoSettings" value={0}
		><i class="fa-solid fa-shield-halved mr-2" />{m.securitySettings()}</Tab
	>
</TabGroup>
{#if tabSet === 0}
	<div class="p-4 flex flex-col space-y-4">
		<div class="flex flex-col">
			<h3 class="h3 font-medium">{m.securitySettings()}</h3>
			<p class="text-sm text-surface-800">{m.securitySettingsDescription()}</p>
		</div>
		<hr />
		<div class="flow-root">
			<dl class="-my-3 divide-y divide-surface-100 text-sm">
				<div class="grid grid-cols-1 gap-1 py-3 sm:grid-cols-3 sm:gap-4">
					<dt class="font-medium">{m.multiFactorAuthentication()}</dt>
					<dd class="text-surface-900 sm:col-span-2">
						<div class="card p-4 bg-inherit w-1/2 flex flex-col space-y-3">
							<div>
								<i class="fa-solid fa-mobile-screen-button"></i>
								<span class="flex flex-row space-x-2">
									<h6 class="h6 text-token">{m.authenticatorApps()}</h6>
									<p class="badge variant-soft-secondary">{m.recommended()}</p>
								</span>
								<p class="text-sm text-surface-800">{m.authenticatorAppsDescription()}</p>
							</div>
							{#if data.authenticators.length > 0}
								<button
									class="btn variant-ringed-surface w-fit"
									on:click={(_) => modalConfirm('?/deactivateTOTP')}>{m.disableTOTP()}</button
								>
							{:else}
								<button
									class="btn variant-ringed-surface w-fit"
									on:click={(_) => modalActivateTOTP(data.totp)}>{m.enableTOTP()}</button
								>
							{/if}
						</div>
					</dd>
				</div>
			</dl>
		</div>
	</div>
{/if}
