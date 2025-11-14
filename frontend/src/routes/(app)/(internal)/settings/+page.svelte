<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import WebhookEndpointCreateModal from './webhooks/endpoints/WebhookEndpointCreateModal.svelte';
	import { SSOSettingsSchema, GeneralSettingsSchema, FeatureFlagsSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	let group = $state('general');

	let { data } = $props();

	function modalWebhookEndpointCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: WebhookEndpointCreateModal,
			props: {
				form: data.webhookEndpointCreateForm,
				formAction: '?/createWebhookEndpoint',
				invalidateAll: true
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.createWebhookEndpoint()
		};
		modalStore.trigger(modal);
	}
</script>

<Tabs
	value={group}
	onValueChange={(e) => {
		group = e.value;
	}}
	active="bg-primary-100 text-primary-800 border-b border-primary-800"
>
	{#snippet list()}
		<Tabs.Control value="general"><i class="fa-solid fa-globe"></i> {m.general()}</Tabs.Control>
		<Tabs.Control value="sso"><i class="fa-solid fa-key"></i> {m.sso()}</Tabs.Control>
		<Tabs.Control value="featureFlags"
			><i class="fa-solid fa-flag"></i> {m.featureFlags()}</Tabs.Control
		>
		<Tabs.Control value="integrations"
			><i class="fa-solid fa-plug"></i> {m.integrations()}</Tabs.Control
		>
		<Tabs.Control value="webhooks"
			><span class="flex flex-row gap-2 items-center ml-0"
				><svg width="20px" height="20px" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
					<title>webhook</title>
					<rect width="24" height="24" fill="none" />
					<path
						d="M10.46,19a4.59,4.59,0,0,1-6.37,1.15,4.63,4.63,0,0,1,2.49-8.38l0,1.43a3.17,3.17,0,0,0-2.36,1.36A3.13,3.13,0,0,0,5,18.91a3.11,3.11,0,0,0,4.31-.84,3.33,3.33,0,0,0,.56-1.44v-1l5.58,0,.07-.11a1.88,1.88,0,1,1,.67,2.59,1.77,1.77,0,0,1-.83-1l-4.07,0A5,5,0,0,1,10.46,19m7.28-7.14a4.55,4.55,0,1,1-1.12,9,4.63,4.63,0,0,1-3.43-2.21L14.43,18a3.22,3.22,0,0,0,2.32,1.45,3.05,3.05,0,1,0,.75-6.06,3.39,3.39,0,0,0-1.53.18l-.85.44L12.54,9.2h-.22a1.88,1.88,0,1,1,.13-3.76A1.93,1.93,0,0,1,14.3,7.39a1.88,1.88,0,0,1-.46,1.15l1.9,3.51a4.75,4.75,0,0,1,2-.19M8.25,9.14A4.54,4.54,0,1,1,16.62,5.6a4.61,4.61,0,0,1-.2,4.07L15.18,9a3.17,3.17,0,0,0,.09-2.73A3.05,3.05,0,1,0,9.65,8.6,3.21,3.21,0,0,0,11,10.11l.39.21-3.07,5a1.09,1.09,0,0,1,.1.19,1.88,1.88,0,1,1-2.56-.83,1.77,1.77,0,0,1,1.23-.17l2.31-3.77A4.41,4.41,0,0,1,8.25,9.14Z"
					/>
				</svg>
				{m.webhooks()}</span
			></Tabs.Control
		>
	{/snippet}
	{#snippet content()}
		<Tabs.Panel value="general">
			<div>
				<span class="text-gray-500">{m.generalSettingsDescription()}</span>
				<ModelForm
					form={data.generalSettingForm}
					schema={GeneralSettingsSchema}
					model={data.generalSettingModel}
					cancelButton={false}
					action="/settings?/general"
				/>
			</div>
		</Tabs.Panel>
		<Tabs.Panel value="sso">
			<div>
				<span class="text-gray-500">{m.ssoSettingsDescription()}</span>
				<ModelForm
					form={data.ssoForm}
					schema={SSOSettingsSchema}
					model={data.ssoModel}
					cancelButton={false}
					action="/settings?/sso"
				/>
			</div>
		</Tabs.Panel>
		<Tabs.Panel value="featureFlags">
			<div>
				<span class="text-gray-500">{m.configureFeatureFlags()}</span>
				<ModelForm
					form={data.featureFlagForm}
					schema={FeatureFlagsSchema}
					model={data.featureFlagModel}
					cancelButton={false}
					action="/settings?/featureFlags"
				/>
			</div>
		</Tabs.Panel>
		<Tabs.Panel value="webhooks">
			<div class="flex flex-col gap-2">
				<span class="text-gray-500">{m.configureOutgoingWebhooks()}</span>
				<span class="font-semibold">{m.webhookEndpoints()}</span>
				<button
					class="btn preset-filled-primary-500 w-fit"
					on:click={modalWebhookEndpointCreateForm}>{m.createWebhookEndpoint()}</button
				>
				{#each data.webhookEndpoints as endpoint}
					<a
						href="/settings/webhooks/endpoints/{endpoint.id}"
						class="block mt-2 text-blue-600 hover:underline"
					>
						{endpoint.name} - {endpoint.url}</a
					>
				{/each}
			</div>
		</Tabs.Panel>
	{/snippet}
</Tabs>
