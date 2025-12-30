<script lang="ts">
	import { m } from '$paraglide/messages';
	import { copy } from '@svelte-put/copy';
	import type { SuperForm } from 'sveltekit-superforms';
	import TextField from './TextField.svelte';
	import { page } from '$app/stores';

	import { getFlash } from 'sveltekit-flash-message';
	const flash = getFlash(page);

	interface Props {
		field: string;
		form: SuperForm<any>;
	}

	let { form, field = 'secret' }: Props = $props();

	const formStore = form?.form;

	let generatedSecret = $state('');

	function generateSecret() {
		const randomBytes = new Uint8Array(48);
		crypto.getRandomValues(randomBytes);
		const randomString = btoa(String.fromCharCode.apply(null, Array.from(randomBytes)))
			.replace(/\+/g, '-')
			.replace(/\//g, '_')
			.replace(/=+$/, '');
		generatedSecret = `whsec_${randomString}`;
		$formStore.secret = generatedSecret;
	}

	function copySecret() {
		if (!generatedSecret) return;

		navigator.clipboard.writeText(generatedSecret).then(() => {
			flash.set({
				type: 'success',
				message: m.secretCopiedToClipboard()
			});
		});
	}
</script>

<div class="w-full flex flex-col items-center gap-2">
	<div class="w-full flex flex-row gap-2 items-center">
		<TextField
			{form}
			{field}
			type="password"
			label={m.secret()}
			helpText={m.webhookSecretHelpText()}
			classesContainer="w-full"
			autocomplete="new-password"
		/>
		<button
			type="button"
			class="btn px-2 py-1 preset-tonal-surface border border-surface-500 transition-transform active:scale-95"
			onclick={generateSecret}>{m.generate()}</button
		>
	</div>
	{#if generatedSecret}
		<div class="flex flex-col card p-2 preset-tonal-warning w-full">
			<p>{m.webhookSharedSecretShownOnce()}</p>
			<span class="flex flex-row gap-2 preset-tonal items-center card pl-2">
				<pre class="overflow-x-auto flex-grow break-all">{generatedSecret}</pre>
				<button
					type="button"
					class="btn px-2 py-1 preset-tonal-surface border border-surface-500 rounded-l-none transition-transform active:scale-95"
					use:copy={{ text: generatedSecret }}
					onclick={copySecret}><i class="fa-solid fa-copy mr-2"></i>{m.copy()}</button
				></span
			>
		</div>
	{/if}
</div>
