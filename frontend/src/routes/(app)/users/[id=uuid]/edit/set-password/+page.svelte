<script lang="ts">
	import type { PageData } from './$types';
	import { page } from '$app/stores';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { SetPasswordSchema } from '$lib/utils/schemas';

	export let data: PageData;

	function getUUID() {
		const matches = $page.url.pathname.split('/');
		return matches ? matches[2] : null;
	}
</script>

<div class="flex w-full h-full items-center justify-center">
	<div class="flex flex-col bg-white p-12 w-2/5 rounded-lg shadow-lg items-center space-y-4">
		<div class="bg-primary-300 px-6 py-5 rounded-full text-3xl">
			<i class="fa-solid fa-key" />
		</div>
		<p class="text-gray-600 text-sm text-center">
			You can set the new password here.<br />
			Careful, the user will be disconnected if he has a session running.
		</p>
		<!-- SuperForm with dataType 'form' -->
		<div class="flex w-full">
			<SuperForm
				class="flex flex-col space-y-3 w-full"
				data={data?.form}
				dataType="form"
				let:form
				validators={SetPasswordSchema}
			>
				<input class="input" type="hidden" name="user" value={getUUID()} />
				<TextField type="password" {form} field="new_password" label="New password" mandatory />
				<TextField
					type="password"
					{form}
					field="confirm_new_password"
					label="Confirm new password"
					mandatory
				/>
				<p class="pt-3">
					<button class="btn variant-filled-primary font-semibold w-full" data-testid="save-button" type="submit"
						>Set Password</button
					>
				</p>
			</SuperForm>
		</div>
	</div>
</div>
