<script lang="ts">
	import type { PageData } from './$types';
	import CisoLogo from '$lib/assets/quant.svg';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { ResetPasswordSchema } from '$lib/utils/schemas';
	import Typewriter from 'svelte-typewriter';

	import * as m from '$paraglide/messages.js';
	import { zod } from 'sveltekit-superforms/adapters';

	export let data: PageData;
</script>

<div class="flex mx-auto justify-center items-center h-screen w-screen bg-slate-200">
	<div class="absolute top-5 left-5">
		<div class="flex flex-row w-full space-x-4 pb-3">
			<img class="c" height="200" width="200" src={CisoLogo} alt="Ciso-assistant icon" />
		</div>
	</div>
	<div class="flex w-full items-center justify-center">
		<div id="hellothere" class="flex flex-col justify-center items-center w-3/5 text-gray-900">
			<Typewriter mode="loopOnce" cursor={false} interval={50}>
				<div class="text-2xl unstyled text-center pb-4">
					<span class="text-2xl text-center">{m.helloThere()} 👋</span>
					<span> {m.thisIsCisoAssistant()}. </span>
				</div>
			</Typewriter>
			<Typewriter mode="cascade" cursor={false} interval={45} delay={5000}>
				<div class="text-2xl unstyled text-center">
					<span> {m.yourStreamlined()} </span>
					<span class="font-black"> {m.oneStopShop()} </span>
					<span> {m.forComplianceRiskManagement()}. </span>
				</div>
			</Typewriter>
		</div>
		<div class="flex flex-col bg-white p-12 rounded-lg shadow-lg items-center space-y-4">
			<div class="bg-primary-300 px-6 py-5 rounded-full text-3xl">
				<i class="fa-solid fa-key" />
			</div>
			<p class="text-gray-600 text-sm text-center">
				{m.youCanSetPAsswordHere()}.<br />
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
							data-testid="set-password-btn">{m.setPassword()}</button
						>
					</p>
				</SuperForm>
			</div>
		</div>
	</div>
</div>
