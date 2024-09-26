<script lang="ts">
	import type { PageData } from './$types';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { ChangePasswordSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages';
	import { zod } from 'sveltekit-superforms/adapters';

	export let data: PageData;
</script>

<div class="flex w-full h-full items-center justify-center">
	<div class="flex flex-col bg-white p-12 w-2/5 rounded-lg shadow-lg items-center space-y-4">
		<div class="bg-primary-300 px-6 py-5 rounded-full text-3xl">
			<i class="fa-solid fa-key" />
		</div>
		<p class="text-gray-600 text-sm text-center">
			{m.changePasswordText()}.
		</p>
		<!-- SuperForm with dataType 'form' -->
		<div class="flex w-full">
			<SuperForm
				class="flex flex-col space-y-3 w-full"
				data={data?.form}
				dataType="form"
				let:form
				validators={zod(ChangePasswordSchema)}
			>
				<TextField type="password" {form} field="old_password" label={m.oldPassword()} />
				<TextField type="password" {form} field="new_password" label={m.newPassword()} />
				<TextField
					type="password"
					{form}
					field="confirm_new_password"
					label={m.confirmNewPassword()}
				/>
				<div class="flex flex-row space-x-2 pt-3">
					<a
						class="btn bg-gray-400 text-white font-semibold w-full"
						href="/my-profile"
						data-testid="cancel-button"
						type="button"
					>
						{m.cancel()}
					</a>
					<button
						class="btn variant-filled-primary font-semibold w-full"
						type="submit"
						data-testid="save-button"
					>
						{m.changePassword()}
					</button>
				</div>
			</SuperForm>
		</div>
	</div>
</div>
