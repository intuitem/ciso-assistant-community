<script lang="ts">
	import type { PageData } from './$types';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import HiddenInput from '$lib/components/Forms/HiddenInput.svelte';
	import { ClientSettingsSchema } from '$lib/utils/client-settings';
	import { zod } from 'sveltekit-superforms/adapters';
	import FileInput from '$lib/components/Forms/FileInput.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import * as m from '$paraglide/messages.js';

	export let data: PageData;

	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { getModelInfo } from '$lib/utils/crud.js';

	import type { ModalSettings, ModalComponent, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';

	const modalStore: ModalStore = getModalStore();

	function modalConfirm(id: string, name: string, action: string): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: data.attachmentDeleteForm,
				id: id,
				debug: false,
				URLModel: 'settings',
				formAction: action
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.confirmModalTitle(),
			body: `${m.confirmModalMessage()}: ${name}?`
		};
		modalStore.trigger(modal);
	}
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
		<div class="flex items-center space-x-1">
			<div class="w-full">
				<FileInput
					{form}
					field="logo"
					label={m.logo()}
					helpText={data.settings.logo
						? `${m.attachmentWarningText()}: ${data.settings.logo}`
						: m.logoHelpText()}
					allowedExtensions={['png', 'jpeg', 'jpg', 'svg']}
				/>
			</div>
			{#if data.settings.logo != null}
				<button
					class="btn variant-filled-tertiary h-full"
					type="button"
					on:click={(_) =>
						modalConfirm(
							data.settings.id,
							data.settings.logo,
							'settings/client-settings?/deleteLogo'
						)}
				>
					<i class="fa-solid fa-trash" />
				</button>
			{/if}
		</div>
		<div class="flex items-center space-x-1">
			<div class="w-full">
				<FileInput
					{form}
					field="favicon"
					label={m.favicon()}
					helpText={data.settings.favicon
						? `${m.attachmentWarningText()}: ${data.settings.favicon}`
						: m.faviconHelpText()}
					allowedExtensions={['png', 'jpeg', 'jpg', 'svg', 'ico']}
				/>
			</div>
		</div>
		{#if data.settings.favicon != null}
			<button
				class="btn variant-filled-tertiary h-full"
				type="button"
				on:click={(_) =>
					modalConfirm(
						data.settings.id,
						data.settings.favicon,
						'settings/client-settings?/deleteFavicon'
					)}
			>
				<i class="fa-solid fa-trash" />
			</button>
		{/if}
		<Checkbox
			{form}
			field="show_images_unauthenticated"
			label={m.showImagesUnauthenticated()}
			helpText={m.showImagesUnauthenticatedHelpText()}
		/>
		<button
			class="btn variant-filled-primary font-semibold w-full"
			data-testid="save-button"
			type="submit">{m.save()}</button
		>
	</SuperForm>
{/if}
