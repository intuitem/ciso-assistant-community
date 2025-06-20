<script lang="ts">
	import { run } from 'svelte/legacy';

	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import type { ActionData, PageData } from './$types';
	import ActivateTOTPModal from './mfa/components/ActivateTOTPModal.svelte';

	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import { defaults } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import ListRecoveryCodesModal from './mfa/components/ListRecoveryCodesModal.svelte';
	import { recoveryCodes } from './mfa/utils/stores';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import CreatePatModal from './pat/components/CreatePATModal.svelte';

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

	let group = $state('security');
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

	let hasTOTP = $derived(data.authenticators.some((auth) => auth.type === 'totp'));
	run(() => {
		$recoveryCodes =
			form && Object.hasOwn(form, 'recoveryCodes') ? form.recoveryCodes : data.recoveryCodes;
	});
</script>

<Tabs
	value={group}
	onValueChange={(e) => {
		group = e.value;
	}}
	active="bg-primary-100 text-primary-800 border-b border-primary-800"
>
	{#snippet list()}
		<Tabs.Control value="security"
			><i class="fa-solid fa-shield-halved mr-2"></i>{m.securitySettings()}</Tabs.Control
		>
	{/snippet}
	{#snippet content()}
		<Tabs.Panel value="security">
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
										<div class="card p-4 preset-tonal-warning max-w-[65ch]">
											<i class="fa-solid fa-warning mr-2 text-warning-900"></i>
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
														<p>
															{m.expiresOn({
																date: new Date(pat.expiry).toLocaleDateString(getLocale())
															})}
														</p>
													</span>
													<button
														onclick={(_) => {
															modalConfirmPATDelete(pat.digest);
														}}
														onkeydown={() => modalConfirmPATDelete(pat.digest)}
														class="cursor-pointer hover:text-primary-500"
														data-testid="tablerow-delete-button"
														><i class="fa-solid fa-trash"></i></button
													>
												</li>
											{/each}
										</ul>
										<button class="btn preset-outlined w-fit" onclick={(_) => modalPATCreateForm()}
											>{m.generateNewPersonalAccessToken()}</button
										>
									</div>
								</div>
							</dd>
						</div>
					</dl>
				</div>
			</div>
		</Tabs.Panel>
	{/snippet}
</Tabs>
