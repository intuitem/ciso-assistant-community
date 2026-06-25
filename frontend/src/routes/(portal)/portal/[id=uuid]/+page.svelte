<script lang="ts">
	import { goto } from '$app/navigation';
	import PortalGrid from '$lib/components/PortalGrid/PortalGrid.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	interface PortalItem {
		icon: string;
		title: string;
		description?: string;
		kind: 'create' | 'navigate' | 'external' | 'status' | 'metric' | 'badge' | 'document';
		target: { model?: string; url?: string; token?: string };
	}

	let { data }: { data: PageData } = $props();
	const modalStore = getModalStore();

	function openCreate(model: string, title: string) {
		const entry = data.createForms[model];
		if (!entry) return;
		const component: ModalComponent = {
			ref: CreateModal,
			props: {
				form: entry.createForm,
				model: entry.model,
				formAction: `?/create&model=${encodeURIComponent(model)}`
			}
		};
		const modal: ModalSettings = { type: 'component', component, title };
		modalStore.trigger(modal);
	}

	function trigger(item: PortalItem) {
		if (item.kind === 'create' && item.target.model) openCreate(item.target.model, item.title);
		else if (item.kind === 'navigate' && item.target.url) goto(item.target.url);
		else if (item.kind === 'external' && item.target.url)
			window.open(item.target.url, '_blank', 'noopener');
		else if (item.kind === 'document' && item.target.token)
			window.open(`/trust/documents/${item.target.token}`, '_blank', 'noopener');
	}
</script>

<PortalGrid sections={data.portal?.sections ?? []} onTrigger={trigger} />
