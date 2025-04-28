<script lang="ts">
	import {
		Tab,
		TabGroup,
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '@skeletonlabs/skeleton';
	import type { ActionData, PageData } from './$types';
	import ActivateTOTPModal from './mfa/components/ActivateTOTPModal.svelte';

	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { m } from '$paraglide/messages';
	import ListRecoveryCodesModal from './mfa/components/ListRecoveryCodesModal.svelte';
	import { recoveryCodes } from './mfa/utils/stores';
	import CreatePatModal from './pat/components/CreatePATModal.svelte';
	import { z } from 'zod';
	import { zod } from 'sveltekit-superforms/adapters';
	import { defaults } from 'sveltekit-superforms';

	export let data: PageData;
	export let form: ActionData;

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

	function modalPATCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreatePatModal,
			props: {
				form: data.personalAccessTokenCreateForm
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.generateNewPersonalAccessToken()
		};
		modalStore.trigger(modal);
	}

	function modalConfirmPATDelete(id: string): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: defaults({ id }, zod(z.object({ id: z.string() }))),
				schema: zod(z.object({ id: z.string() })),
				id: id,
				debug: false,
				formAction: '?/deletePAT'
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.confirmModalTitle(),
			body: m.personalAccessTokenDeleteConfirm()
		};
		modalStore.trigger(modal);
	}

	let tabSet = 0;

	$: hasTOTP = data.authenticators.some((auth) => auth.type === 'totp');
	$: $recoveryCodes =
		form && Object.hasOwn(form, 'recoveryCodes') ? form.recoveryCodes : data.recoveryCodes;
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
						<div class="card p-4 bg-inherit w-fit flex flex-col space-y-3">
							<div class="flex flex-col space-y-2">
								<span class="flex flex-row justify-between text-xl">
									<i class="fa-solid fa-mobile-screen-button"></i>
									{#if hasTOTP}
										<i class="fa-solid fa-circle-check text-success-500-400-token"></i>
									{/if}
								</span>
								<span class="flex flex-row space-x-2">
									<h6 class="h6 text-token">{m.authenticatorApp()}</h6>
									<p class="badge h-fit variant-soft-secondary">{m.recommended()}</p>
								</span>
								<p class="text-sm text-surface-800 max-w-[50ch]">
									{m.authenticatorAppDescription()}
								</p>
							</div>
							<div class="flex flex-wrap justify-between gap-2">
								{#if hasTOTP}
									<button
										class="btn variant-ringed-surface w-fit"
										on:click={(_) => modalConfirm('?/deactivateTOTP')}>{m.disableTOTP()}</button
									>
									{#if data.recoveryCodes}
										<button
											class="btn variant-ringed-surface w-fit"
											on:click={(_) => modalListRecoveryCodes()}>{m.listRecoveryCodes()}</button
										>
									{/if}
								{:else}
									<button
										class="btn variant-ringed-surface w-fit"
										on:click={(_) => modalActivateTOTP(data.totp)}>{m.enableTOTP()}</button
									>
								{/if}
							</div>
						</div>
					</dd>
				</div>
			</dl>
			<dl class="-my-3 divide-y divide-surface-100 text-sm">
				<div class="grid grid-cols-1 gap-1 py-3 sm:grid-cols-3 sm:gap-4">
					<dt class="font-medium">{m.personalAccessTokens()}</dt>
					<dd class="text-surface-900 sm:col-span-2">
						<div class="card p-4 bg-inherit w-fit flex flex-col space-y-3">
							<div class="flex flex-col space-y-2">
								<span class="flex flex-row justify-between text-xl">
									<i class="fa-solid fa-key"></i>
									{#if hasTOTP}
										<i class="fa-solid fa-circle-check text-success-500-400-token"></i>
									{/if}
								</span>
								<span class="flex flex-row space-x-2">
									<h6 class="h6 text-token">{m.personalAccessTokens()}</h6>
								</span>
								<p class="text-sm text-surface-800 max-w-[65ch]">
									{m.personalAccessTokensDescription()}
								</p>
								<div class="card p-4 variant-ghost-warning max-w-[65ch]">
									<i class="fa-solid fa-warning mr-2 text-warning-900" />
									{m.personalAccessTokenCreateWarning()}
								</div>
							</div>
							<div class="flex flex-col gap-2">
								<ul class="max-h-72 overflow-y-scroll">
									{#each data.personalAccessTokens as pat}
										<li class="flex flex-row justify-between card p-4 bg-inherit">
											<span class="grid grid-rows-1 grid-cols-2 w-full">
												<p>
													{pat.name}
												</p>
												<p>{m.expiresOn({ date: new Date(pat.expiry).toLocaleDateString() })}</p>
											</span>
											<button
												on:click={(_) => {
													modalConfirmPATDelete(pat.digest);
												}}
												on:keydown={() => modalConfirmPATDelete(pat.digest)}
												class="cursor-pointer hover:text-primary-500"
												data-testid="tablerow-delete-button"><i class="fa-solid fa-trash" /></button
											>
										</li>
									{/each}
								</ul>
								<button
									class="btn variant-ringed-surface w-fit"
									on:click={(_) => modalPATCreateForm()}
									>{m.generateNewPersonalAccessToken()}</button
								>
							</div>
						</div>
					</dd>
				</div>
			</dl>
		</div>
	</div>
{/if}
