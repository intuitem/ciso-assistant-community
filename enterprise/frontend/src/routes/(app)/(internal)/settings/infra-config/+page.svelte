<script lang="ts">
	import { m } from '$paraglide/messages';
	import { page } from '$app/stores';
	import { InfraConfigSchema, MAX_ALLOWED_IPS } from '$lib/utils/infra-config';
	import IpListInput from '$lib/components/Settings/IpListInput.svelte';
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

	const allowedIps = $derived(($form.allowed_ips ?? []) as string[]);
</script>

<form
	bind:this={formEl}
	method="POST"
	action="/settings/infra-config?/saveInfraConfig"
	use:enhance
	class="flex flex-col gap-6"
>
	<span class="text-surface-600-400">{m.infraConfigDescription()}</span>

	<div class="flex flex-col gap-3">
		<h3 class="text-base font-semibold flex items-center gap-2">
			<i class="fa-solid fa-network-wired text-sm text-primary-500"></i>
			{m.allowedIps()}
			<span class="text-xs font-normal text-surface-500"
				>({allowedIps.length}/{MAX_ALLOWED_IPS})</span
			>
		</h3>

		<IpListInput
			bind:ips={$form.allowed_ips}
			idPrefix="allowed-ip"
			allMatchWarning={m.allowsAllIpsWarning()}
			emptyText={m.noAllowedIpsYet()}
		/>
	</div>

	<div>
		<button type="submit" class="btn preset-filled-primary-500" disabled={$submitting}>
			{m.save()}
		</button>
	</div>
</form>
