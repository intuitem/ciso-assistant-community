<script lang="ts">
	import { m } from '$paraglide/messages';
	import { page } from '$app/stores';
	import {
		InfraConfigSchema,
		MAX_ALLOWED_IPS,
		MIN_MAX_FAILED_LOGIN_ATTEMPTS,
		MAX_MAX_FAILED_LOGIN_ATTEMPTS,
		MAX_TIME_WINDOW_SIZE,
		MAX_BAN_TIME,
		MAX_ABSOLUTE_BAN_TIME
	} from '$lib/utils/infra-config';
	import IpListInput from '$lib/components/Settings/IpListInput.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import { superForm, type SuperForm } from 'sveltekit-superforms/client';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { getFlash } from 'sveltekit-flash-message';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const modalStore: ModalStore = getModalStore();
	const flash = getFlash(page);

	let formEl: HTMLFormElement;
	let confirmedEmpty = false;

	const superFormObject = superForm(data.form, {
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
	const { form, enhance, submitting } = superFormObject;
	// `Checkbox` and `NumberField` take a loosely typed form (same as the other settings forms).
	const formProp = superFormObject as SuperForm<any>;

	const allowedIps = $derived(($form.allowed_ips ?? []) as string[]);
	const notRateLimitedIps = $derived(($form.not_rate_limited_ips ?? []) as string[]);
	const proxyIps = $derived(($form.proxy_ips ?? []) as string[]);
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

	<div class="flex flex-col gap-3">
		<h3 class="text-base font-semibold flex items-center gap-2">
			<i class="fa-solid fa-gauge-high text-sm text-primary-500"></i>
			{m.rateLimiting()}
		</h3>
		<span class="text-surface-600-400 text-sm">{m.rateLimitingDescription()}</span>

		<div class="flex flex-col gap-4 max-w-md">
			<Checkbox
				form={formProp}
				field="is_rate_limit_activated"
				label={m.isRateLimitActivated()}
				helpText={m.isRateLimitActivatedHelpText()}
			/>
			<NumberField
				form={formProp}
				field="max_failed_login_attempts"
				label={m.maxFailedLoginAttempts()}
				helpText={m.maxFailedLoginAttemptsHelpText()}
				min={MIN_MAX_FAILED_LOGIN_ATTEMPTS}
				max={MAX_MAX_FAILED_LOGIN_ATTEMPTS}
				step={1}
			/>
			<NumberField
				form={formProp}
				field="time_window_size"
				label={m.timeWindowSize()}
				helpText={m.timeWindowSizeHelpText()}
				min={1}
				max={MAX_TIME_WINDOW_SIZE}
				step={1}
			/>
			<NumberField
				form={formProp}
				field="ban_time"
				label={m.banTime()}
				helpText={m.banTimeHelpText({ max: MAX_ABSOLUTE_BAN_TIME })}
				min={1}
				max={MAX_BAN_TIME}
				step={1}
			/>
		</div>
	</div>

	<div class="flex flex-col gap-3">
		<h3 class="text-base font-semibold flex items-center gap-2">
			<i class="fa-solid fa-circle-check text-sm text-primary-500"></i>
			{m.notRateLimitedIps()}
			<span class="text-xs font-normal text-surface-500"
				>({notRateLimitedIps.length}/{MAX_ALLOWED_IPS})</span
			>
		</h3>
		<span class="text-surface-600-400 text-sm">{m.notRateLimitedIpsDescription()}</span>

		<IpListInput
			bind:ips={$form.not_rate_limited_ips}
			idPrefix="not-rate-limited-ip"
			allMatchWarning={m.excludesAllIpsWarning()}
			emptyText={m.noNotRateLimitedIpsYet()}
		/>
	</div>

	<div class="flex flex-col gap-3">
		<h3 class="text-base font-semibold flex items-center gap-2">
			<i class="fa-solid fa-server text-sm text-primary-500"></i>
			{m.proxyIps()}
			<span class="text-xs font-normal text-surface-500">({proxyIps.length}/{MAX_ALLOWED_IPS})</span
			>
		</h3>
		<span class="text-surface-600-400 text-sm">{m.proxyIpsDescription()}</span>

		<IpListInput
			bind:ips={$form.proxy_ips}
			idPrefix="proxy-ip"
			allMatchWarning={m.trustsAllProxiesWarning()}
			emptyText={m.noProxyIpsYet()}
		/>
	</div>

	<div>
		<button type="submit" class="btn preset-filled-primary-500" disabled={$submitting}>
			{m.save()}
		</button>
	</div>
</form>
