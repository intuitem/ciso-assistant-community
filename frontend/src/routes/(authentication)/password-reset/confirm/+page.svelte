<script lang="ts">
	import type { PageData } from './$types';
	import Logo from '$lib/components/Logo/Logo.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { ResetPasswordSchema } from '$lib/utils/schemas';
	import { zod } from 'sveltekit-superforms/adapters';

	export let data: PageData;
</script>

<div class="flex mx-auto justify-center items-center h-screen w-screen bg-slate-200">
	<div class="absolute top-5 left-5">
		<div class="flex flex-row w-full space-x-4 pb-3">
			<Logo />
		</div>
	</div>
	<div class="flex w-full items-center justify-center">
		<div class="flex flex-col bg-white p-12 rounded-lg shadow-lg items-center space-y-4">
			<div class="bg-primary-300 px-6 py-5 rounded-full text-3xl">
				<i class="fa-solid fa-key" />
			</div>
			<p class="text-gray-600 text-sm text-center">
				You can reset your password here.<br />
			</p>
			<!-- SuperForm with dataType 'form' -->
			<div class="flex w-full">
				<SuperForm
					class="flex flex-col space-y-3 w-full"
					data={data?.form}
					dataType="form"
					let:form
					validators={zod(ResetPasswordSchema)}
				>
					<TextField type="password" {form} field="new_password" label="New password" />
					<TextField
						type="password"
						{form}
						field="confirm_new_password"
						label="Confirm new password"
					/>
					<p class="pt-3">
						<button
							class="btn variant-filled-primary font-semibold w-full"
							type="submit"
							data-testid="set-password-btn">Reset Password</button
						>
					</p>
				</SuperForm>
			</div>
		</div>
	</div>
</div>
