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

	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';

	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

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
		localStorage.removeItem('favicon');
	}
</script>

{#if data && Object.hasOwn(data, 'form')}
	<SuperForm
		dataType="form"
		enctype="multipart/form-data"
		data={data.form}
		validators={zod(ClientSettingsSchema)}
		action="/settings/client-settings?/editClientSettings"
		class="flex flex-col space-y-3"
	>
		{#snippet children({ form })}
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
						class="btn preset-filled-tertiary-500 h-full"
						type="button"
						data-testid="delete-logo-button"
						onclick={(_) =>
							modalConfirm(
								data.settings.id,
								data.settings.logo,
								'/settings/client-settings?/deleteLogo'
							)}
					>
						<i class="fa-solid fa-trash"></i>
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
				{#if data.settings.favicon != null}
					<button
						class="btn preset-filled-tertiary-500 h-full"
						type="button"
						data-testid="delete-favicon-button"
						onclick={(_) =>
							modalConfirm(
								data.settings.id,
								data.settings.favicon,
								'/settings/client-settings?/deleteFavicon'
							)}
					>
						<i class="fa-solid fa-trash"></i>
					</button>
				{/if}
			</div>
			<Checkbox
				{form}
				field="show_images_unauthenticated"
				label={m.showImagesUnauthenticated()}
				helpText={m.showImagesUnauthenticatedHelpText()}
			/>
			<button
				class="btn preset-filled-primary-500 font-semibold w-full"
				data-testid="save-button"
				type="submit">{m.save()}</button
			>
		{/snippet}
	</SuperForm>
{/if}
