<script lang="ts">
	import { goto } from '$app/navigation';
	import { deserialize } from '$app/forms';
	import { isSafeExternalUrl } from '$lib/utils/external-links';
	import { m } from '$paraglide/messages';
	import PortalGrid from '$lib/components/PortalGrid/PortalGrid.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import AssessmentLaunchModal from '$lib/components/Modals/AssessmentLaunchModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	interface PortalItem {
		id?: string;
		icon: string;
		title: string;
		description?: string;
		kind:
			| 'create'
			| 'navigate'
			| 'external'
			| 'metric'
			| 'certificationDocument'
			| 'framework'
			| 'assessment';
		target: {
			model?: string;
			url?: string;
			token?: string;
			dest?: string;
			folder?: string;
			user_names?: boolean;
		};
	}

	let { data }: { data: PageData } = $props();
	const modalStore = getModalStore();

	let launching = $state(false);
	let launchError = $state('');

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

	// Instantiate the audit configured on the tile, then jump to it. The server reads the
	// framework/mode from the stored tile config — we only send which tile. The domain is
	// forced by the author here; tiles that let the clicker pick go through the modal below.
	async function launchAssessment(item: PortalItem) {
		if (launching) return;
		launching = true;
		launchError = '';
		try {
			const body = new FormData();
			body.append('item', item.id ?? '');
			const res = await fetch('?/launchAssessment', { method: 'POST', body });
			const result: any = deserialize(await res.text());
			if (result.type === 'success' && result.data?.redirect) {
				await goto(result.data.redirect);
			} else {
				launchError = result.data?.error || m.assessmentLaunchFailed();
			}
		} catch {
			launchError = m.assessmentLaunchFailed();
		} finally {
			launching = false;
		}
	}

	function openLaunchModal(item: PortalItem) {
		const component: ModalComponent = {
			ref: AssessmentLaunchModal,
			props: {
				item: item.id ?? '',
				showName: !!item.target.user_names,
				defaultName: item.title,
				showDomain: !item.target.folder,
				domains: data.domains ?? [],
				personalFoldersEnabled: data.personalFoldersEnabled ?? false
			}
		};
		const modal: ModalSettings = { type: 'component', component, title: item.title };
		modalStore.trigger(modal);
	}

	function trigger(item: PortalItem) {
		if (item.kind === 'create' && item.target.model) openCreate(item.target.model, item.title);
		else if (item.kind === 'navigate' && item.target.model) goto(`/${item.target.model}`);
		else if (item.kind === 'external' && isSafeExternalUrl(item.target.url))
			window.open(item.target.url, '_blank', 'noopener,noreferrer');
		else if (item.kind === 'certificationDocument') {
			if (item.target.dest === 'document' && item.target.token)
				window.open(`/trust/documents/${item.target.token}`, '_blank', 'noopener,noreferrer');
			else if (isSafeExternalUrl(item.target.url))
				window.open(item.target.url, '_blank', 'noopener,noreferrer');
		} else if (item.kind === 'assessment') {
			// Launch directly only when nothing needs to be asked at click time.
			if (!item.target.folder || item.target.user_names) openLaunchModal(item);
			else launchAssessment(item);
		}
	}
</script>

{#if launchError}
	<aside class="card preset-tonal-error mb-6 p-4 text-sm">
		<i class="fa-solid fa-triangle-exclamation mr-2"></i>{launchError}
	</aside>
{/if}

<PortalGrid sections={data.portal?.sections ?? []} onTrigger={trigger} />
