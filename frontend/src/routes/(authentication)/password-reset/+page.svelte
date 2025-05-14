<script lang="ts">
	import type { PageData } from './$types';
	import { emailSchema } from '$lib/utils/schemas';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';

	import { m } from '$paraglide/messages';
	import { zod } from 'sveltekit-superforms/adapters';
	import Logo from '$lib/components/Logo/Logo.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="flex mx-auto justify-center items-center h-screen w-screen bg-slate-200">
	<div class="absolute top-5 left-5">
		<div class="flex flex-row w-full space-x-4 pb-3">
			<Logo />
		</div>
	</div>
	<div class="flex items-center justify-center p-10 space-x-4 w-full">
		<div class="lg:w-1/4 p-6 shadow-lg rounded-lg bg-white">
			<div id="password_reset" class="flex flex-col items-center space-y-4">
				<div class="bg-primary-300 px-6 py-5 rounded-full text-3xl">
					<i class="fa-solid fa-lock"></i>
				</div>
				<h3 class="font-bold leading-tight tracking-tight text-gray-900 md:text-2xl">
					{m.forgtPassword()}
				</h3>
				<p class="text-center text-gray-600 text-sm">
					{m.enterYourEmail()}.
				</p>
				<div>
					<!-- SuperForm with dataType 'form' -->
					<SuperForm
						class="flex flex-col space-y-3"
						data={data?.form}
						dataType="form"
						
						validators={zod(emailSchema)}
					>
						{#snippet children({ form })}
												<TextField type="email" {form} field="email" label={m.email()} />
							<p class="pt-3">
								<button
									class="btn preset-filled-primary-500 font-semibold w-full"
									data-testid="send-btn"
									type="submit">{m.send()}</button
								>
							</p>
																	{/snippet}
										</SuperForm>
				</div>
				<a
					href="/login"
					class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
				>
					<i class="fa-solid fa-arrow-left"></i>
					<p class="">{m.goBackToLogin()}</p>
				</a>
			</div>
		</div>
	</div>
</div>
