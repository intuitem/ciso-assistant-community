<script lang="ts">
	import type { PageData } from './$types';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { ChangePasswordSchema } from '$lib/utils/schemas';

	export let data: PageData;
</script>

<div class="flex w-full h-full items-center justify-center">
	<div class="flex flex-col bg-white p-12 w-2/5 rounded-lg shadow-lg items-center space-y-4">
		<div class="bg-primary-300 px-6 py-5 rounded-full text-3xl">
			<i class="fa-solid fa-key" />
		</div>
		<p class="text-gray-600 text-sm text-center">
			You can change your password here.<br />
			You'll need to log in with your new password after this operation.
		</p>
		<!-- SuperForm with dataType 'form' -->
		<div class="flex w-full">
			<SuperForm
				class="flex flex-col space-y-3 w-full"
				data={data?.form}
				dataType="form"
				let:form
				validators={ChangePasswordSchema}
			>
				<TextField type="password" {form} field="old_password" label="Old password" />
				<TextField type="password" {form} field="new_password" label="New password" />
				<TextField
					type="password"
					{form}
					field="confirm_new_password"
					label="Confirm new password"
				/>
				<p class="pt-3">
					<button class="btn variant-filled-primary font-semibold w-full" type="submit"
						>Change Password</button
					>
				</p>
			</SuperForm>
		</div>
	</div>
</div>
