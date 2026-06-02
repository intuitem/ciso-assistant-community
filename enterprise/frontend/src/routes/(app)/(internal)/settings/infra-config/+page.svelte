<script lang="ts">
	import { m } from '$paraglide/messages';
	import { page } from '$app/stores';
	import {
		InfraConfigSchema,
		isIpOrCidr,
		IP_INPUT_MAXLENGTH,
		MAX_ALLOWED_IPS
	} from '$lib/utils/infra-config';
	import { superForm } from 'sveltekit-superforms/client';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { getFlash } from 'sveltekit-flash-message';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const modalStore: ModalStore = getModalStore();
	const flash = getFlash(page);

	let formEl: HTMLFormElement;
	let confirmedEmpty = false;

	const { form, enhance, submitting } = superForm(data.form, {
		dataType: 'json',
		validators: zod(InfraConfigSchema),
		// Keep the user on this tab after save: don't let SvelteKit re-apply the
		// action / invalidate the layout, which would reset the active tab state.
		// Feedback is surfaced via the standard flash toast (set client-side) below.
		applyAction: false,
		invalidateAll: false,
		resetForm: false,
		onSubmit: ({ cancel }) => {
			// Confirm before saving an empty allowlist (security-sensitive).
			if (($form.allowed_ips ?? []).length === 0 && !confirmedEmpty) {
				cancel();
				modalStore.trigger({
					type: 'confirm',
					title: m.warning(),
					body: m.confirmEmptyAllowlist(),
					response: (r: boolean) => {
						if (r) {
							confirmedEmpty = true;
							formEl.requestSubmit();
						}
					}
				});
			}
		},
		onUpdated: ({ form }) => {
			confirmedEmpty = false;
			if (form.message?.text) {
				flash.set({
					type: form.message.type === 'error' ? 'error' : 'success',
					message: form.message.text
				});
			}
		}
	});

	let newIp = $state('');
	let inputError = $state('');

	const allowedIps = $derived(($form.allowed_ips ?? []) as string[]);
	const allowsAll = $derived(allowedIps.some((ip) => ['0.0.0.0/0', '::/0'].includes(ip.trim())));

	function addIp() {
		const ip = newIp.trim();
		if (!ip) {
			inputError = m.enterIpFirst();
			return;
		}
		if (allowedIps.length >= MAX_ALLOWED_IPS) {
			inputError = m.tooManyAllowedIps({ max: MAX_ALLOWED_IPS });
			return;
		}
		if (!isIpOrCidr(ip)) {
			inputError = m.invalidIpOrCidr();
			return;
		}
		if (allowedIps.includes(ip)) {
			inputError = m.ipAlreadyAdded();
			return;
		}
		$form.allowed_ips = [...allowedIps, ip];
		newIp = '';
		inputError = '';
	}

	function removeIp(index: number) {
		$form.allowed_ips = allowedIps.filter((_, i) => i !== index);
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addIp();
		}
	}
</script>

<form
	bind:this={formEl}
	method="POST"
	action="/settings/infra-config?/saveInfraConfig"
	use:enhance
	class="flex flex-col gap-6"
>
	<span class="text-gray-500">{m.infraConfigDescription()}</span>

	<div class="flex flex-col gap-3">
		<h3 class="text-base font-semibold flex items-center gap-2">
			<i class="fa-solid fa-network-wired text-sm text-primary-500"></i>
			{m.allowedIps()}
			<span class="text-xs font-normal text-gray-400">({allowedIps.length}/{MAX_ALLOWED_IPS})</span>
		</h3>

		<div class="flex items-start gap-2">
			<div class="flex flex-col gap-1 w-full max-w-md">
				<input
					id="allowed-ip-input"
					name="allowed-ip-input"
					type="text"
					bind:value={newIp}
					onkeydown={onKeydown}
					oninput={() => (inputError = '')}
					placeholder={m.ipAddressOrCidr()}
					aria-label={m.ipAddressOrCidr()}
					aria-invalid={inputError ? 'true' : undefined}
					aria-describedby={inputError ? 'allowed-ip-error' : undefined}
					autocomplete="off"
					maxlength={IP_INPUT_MAXLENGTH}
					class="input font-mono {inputError ? 'border border-error-500' : ''}"
					data-testid="allowed-ip-input"
				/>
				{#if inputError}
					<span id="allowed-ip-error" class="text-error-500 text-xs">{inputError}</span>
				{/if}
			</div>
			<button
				type="button"
				class="btn preset-tonal-primary-500"
				onclick={addIp}
				disabled={allowedIps.length >= MAX_ALLOWED_IPS}
			>
				<i class="fa-solid fa-plus mr-1"></i>
				{m.add()}
			</button>
		</div>

		{#if allowsAll}
			<p class="text-warning-700 text-sm flex items-center gap-2">
				<i class="fa-solid fa-triangle-exclamation"></i>
				{m.allowsAllIpsWarning()}
			</p>
		{/if}

		{#if allowedIps.length > 0}
			<div class="flex flex-wrap gap-2 max-h-64 overflow-y-auto" data-testid="allowed-ip-list">
				{#each allowedIps as ip, i (ip)}
					<span
						class="badge preset-tonal-surface flex items-center gap-2 font-mono max-w-xs"
						data-testid="allowed-ip-chip"
					>
						<span class="truncate">{ip}</span>
						<button
							type="button"
							aria-label={m.removeIp({ ip })}
							class="hover:text-error-500 cursor-pointer shrink-0"
							onclick={() => removeIp(i)}
						>
							<i class="fa-solid fa-xmark"></i>
						</button>
					</span>
				{/each}
			</div>
		{:else}
			<p class="text-gray-400 italic">{m.noAllowedIpsYet()}</p>
		{/if}
	</div>

	<div>
		<button type="submit" class="btn preset-filled-primary-500" disabled={$submitting}>
			{m.save()}
		</button>
	</div>
</form>
