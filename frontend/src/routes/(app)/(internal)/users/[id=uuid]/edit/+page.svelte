<script lang="ts">
	import { page } from '$app/state';
	import { enhance } from '$app/forms';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { UserEditSchema } from '$lib/utils/schemas';
	import { getModalStore } from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const modalStore = getModalStore();
	let resetMFAForm: HTMLFormElement | undefined = $state();

	function confirmResetMFA() {
		modalStore.trigger({
			type: 'confirm',
			title: m.resetMFA(),
			body: m.resetMFAConfirmation(),
			buttonTextConfirm: m.resetMFA(),
			response: (confirmed: boolean) => {
				if (!confirmed) return;
				resetMFAForm?.requestSubmit();
			}
		});
	}
</script>

<div class="card bg-white shadow-sm p-4">
	<ModelForm form={data.form} schema={UserEditSchema} model={data.model} action="?/updateUser" />
</div>

{#if data.object.is_local}
	<div class="card bg-white shadow-sm p-4 mt-2">
		<p class="text-gray-500 text-sm">
			{m.setTemporaryPassword1()}
			<a
				href="{page.url.pathname}/set-password"
				class="text-primary-700 hover:text-primary-500"
				data-testid="set-password-btn">{m.setTemporaryPassword()}</a
			>. {m.setTemporaryPassword2()}.
		</p>
	</div>
{/if}

{#if data.object.has_mfa_enabled}
	<div class="card bg-white shadow-sm p-4 mt-2">
		<p class="text-gray-500 text-sm">
			{m.resetMFADescription()}
			<button
				type="button"
				class="text-warning-700 hover:text-warning-500 cursor-pointer"
				data-testid="reset-mfa-btn"
				onclick={confirmResetMFA}>{m.resetMFA()}</button
			>.
		</p>
	</div>
	<form
		bind:this={resetMFAForm}
		method="POST"
		action="?/resetMFA"
		class="hidden"
		use:enhance
	></form>
{/if}
