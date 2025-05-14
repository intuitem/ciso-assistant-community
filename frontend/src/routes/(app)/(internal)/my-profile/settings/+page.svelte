<script lang="ts">
	import { run } from 'svelte/legacy';

	import {
		Tab,
		type ModalComponent,
		type ModalSettings,
		type ModalStore, Tabs } from '@skeletonlabs/skeleton-svelte';
	import type { ActionData, PageData } from './$types';
	import ActivateTOTPModal from './mfa/components/ActivateTOTPModal.svelte';

	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { m } from '$paraglide/messages';
	import ListRecoveryCodesModal from './mfa/components/ListRecoveryCodesModal.svelte';
	import { recoveryCodes } from './mfa/utils/stores';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

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
			body: m.disableTOTPConfirm()
		};
		modalStore.trigger(modal);
	}

	function modalListRecoveryCodes(): void {
		const recoveryCodesModalComponent: ModalComponent = {
			ref: ListRecoveryCodesModal
		};
		const recoveryCodesModal: ModalSettings = {
			type: 'component',
			component: recoveryCodesModalComponent,
			// Data
			title: m.recoveryCodes(),
			body: m.listRecoveryCodesHelpText()
		};
		modalStore.trigger(recoveryCodesModal);
	}

	let tabSet = $state(0);

	let hasTOTP = $derived(data.authenticators.some((auth) => auth.type === 'totp'));
	run(() => {
		$recoveryCodes =
			form && Object.hasOwn(form, 'recoveryCodes') ? form.recoveryCodes : data.recoveryCodes;
	});
</script>

<Tabs active="bg-primary-100 text-primary-800 border-b border-primary-800">
	<Tab bind:group={tabSet} name="ssoSettings" value={0}
		><i class="fa-solid fa-shield-halved mr-2"></i>{m.securitySettings()}</Tab
	>
</Tabs>
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
						<div class="card p-4 bg-inherit w-fit flex flex-col space-y-3">
							<div class="flex flex-col space-y-2">
								<span class="flex flex-row justify-between text-xl">
									<i class="fa-solid fa-mobile-screen-button"></i>
									{#if hasTOTP}
										<i class="fa-solid fa-circle-check text-success-600-400"></i>
									{/if}
								</span>
								<span class="flex flex-row space-x-2">
									<h6 class="h6 base-font-color">{m.authenticatorApp()}</h6>
									<p class="badge h-fit preset-tonal-secondary">{m.recommended()}</p>
								</span>
								<p class="text-sm text-surface-800 max-w-[50ch]">
									{m.authenticatorAppDescription()}
								</p>
							</div>
							<div class="flex flex-wrap justify-between gap-2">
								{#if hasTOTP}
									<button
										class="btn preset-outlined-surface-500 w-fit"
										onclick={(_) => modalConfirm('?/deactivateTOTP')}>{m.disableTOTP()}</button
									>
									{#if data.recoveryCodes}
										<button
											class="btn preset-outlined-surface-500 w-fit"
											onclick={(_) => modalListRecoveryCodes()}>{m.listRecoveryCodes()}</button
										>
									{/if}
								{:else}
									<button
										class="btn preset-outlined-surface-500 w-fit"
										onclick={(_) => modalActivateTOTP(data.totp)}>{m.enableTOTP()}</button
									>
								{/if}
							</div>
						</div>
					</dd>
				</div>
			</dl>
		</div>
	</div>
{/if}
