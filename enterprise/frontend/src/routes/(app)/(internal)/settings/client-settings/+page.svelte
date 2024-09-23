<script lang="ts">
	import type { PageData } from './$types';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import HiddenInput from '$lib/components/Forms/HiddenInput.svelte';
	import { ClientSettingsSchema } from '$lib/utils/client-settings';
	import { zod } from 'sveltekit-superforms/adapters';
	import FileInput from '$lib/components/Forms/FileInput.svelte';
	import * as m from '$paraglide/messages.js';

	export let data: PageData;
</script>

{#if data && Object.hasOwn(data, 'form')}
	<SuperForm
		dataType="form"
		enctype="multipart/form-data"
		data={data.form}
		let:form
		validators={zod(ClientSettingsSchema)}
		action="/settings/client-settings?/editClientSettings"
		class="flex flex-col space-y-3"
	>
		<HiddenInput {form} field="id" />
		<TextField {form} field="name" label={m.name()} />
		<FileInput
			{form}
			field="logo"
			label={m.logo()}
			helpText={data.settings.logo
				? `${m.attachmentWarningText()}: ${data.settings.logo}`
				: m.logoHelpText()}
			accept="image/*"
		/>
		<FileInput
			{form}
			field="favicon"
			label={m.favicon()}
			helpText={data.settings.favicon
				? `${m.attachmentWarningText()}: ${data.settings.favicon}`
				: m.faviconHelpText()}
			accept="image/*"
		/>
		<button
			class="btn variant-filled-primary font-semibold w-full"
			data-testid="save-button"
			type="submit">{m.save()}</button
		>
	</SuperForm>
{/if}
