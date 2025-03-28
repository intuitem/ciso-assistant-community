<script lang="ts">
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { loginSchema } from '$lib/utils/schemas';

	import { page } from '$app/stores';
	import { redirectToProvider } from '$lib/allauth.js';
	import { zod } from 'sveltekit-superforms/adapters';
	import MfaAuthenticateModal from './mfa/components/MFAAuthenticateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '@skeletonlabs/skeleton';

	import { m } from '$paraglide/messages';

	export let data: any;
	export let form: any;

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
			title: m.mfaAuthenticateTitle(),
			body: m.enterCodeGeneratedByApp()
		};
		modalStore.trigger(modal);
	}

	$: form && form.mfaFlow ? modalMFAAuthenticate() : null;
</script>

<div class="flex flex-col w-7/8 lg:w-3/4 p-10 rounded-lg shadow-lg bg-white bg-opacity-[.90]">
	<div data-testid="login" class="flex flex-col w-full items-center space-y-4">
		<div class="bg-primary-300 px-6 py-5 rounded-full text-3xl">
			<i class="fa-solid fa-right-to-bracket" />
		</div>
		<h3
			class="font-bold leading-tight tracking-tight md:text-2xl bg-gradient-to-r from-pink-500 to-violet-600 bg-clip-text text-transparent"
		>
			{m.logIntoYourAccount()}
		</h3>
		<p class="text-center text-gray-600 text-sm">
			{m.youNeedToLogIn()}
		</p>
		<div class="w-full">
			<!-- SuperForm with dataType 'form' -->
			<SuperForm
				class="flex flex-col space-y-3"
				data={data?.form}
				dataType="form"
				let:form
				validators={zod(loginSchema)}
				action="?/login&next={$page.url.searchParams.get('next') || '/'}"
			>
				<TextField type="email" {form} field="username" label={m.email()} />
				<TextField type="password" {form} field="password" label={m.password()} />
				<div class="flex flex-row justify-end">
					<a
						href="/password-reset"
						class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
						data-testid="forgot-password-btn"
					>
						<p class="">{m.forgtPassword()}?</p>
					</a>
				</div>
				<p class="">
					<button
						class="btn variant-filled-primary font-semibold w-full"
						data-testid="login-btn"
						type="submit">{m.login()}</button
					>
				</p>
			</SuperForm>
		</div>
		{#if data.SSOInfo.is_enabled}
			<div class="flex items-center justify-center w-full space-x-2">
				<hr class="w-64 items-center bg-gray-200 border-0" />
				<span class="flex items-center text-gray-600 text-sm">{m.or()}</span>
				<hr class="w-64 items-center bg-gray-200 border-0" />
			</div>
			<button
				class="btn bg-gradient-to-l from-violet-800 to-violet-400 text-white font-semibold w-1/2"
				on:click={() =>
					redirectToProvider(data.SSOInfo.sp_entity_id, data.SSOInfo.callback_url, 'login')}
				>{m.loginSSO()}</button
			>
		{/if}
	</div>
</div>
