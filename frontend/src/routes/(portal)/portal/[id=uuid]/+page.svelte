<script lang="ts">
	import { goto } from '$app/navigation';
	import { goto as breadcrumbGoto } from '$lib/utils/breadcrumbs';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { deserialize } from '$app/forms';
	import { openPortalExternal } from '$lib/utils/external-links';
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
			| 'assessment'
			| 'quickForm';
		target: {
			model?: string;
			url?: string;
			token?: string;
			dest?: string;
			folder?: string;
			user_names?: boolean;
			quick_form?: string;
		};
	}

	let { data }: { data: PageData } = $props();
	const modalStore = getModalStore();

	let launching = $state(false);
	let launchError = $state('');
	// Set when a tile handed back an existing draft rather than creating a response.
	let resumedRef = $state('');

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
			const action = item.kind === 'quickForm' ? '?/launchQuickForm' : '?/launchAssessment';
			const res = await fetch(action, { method: 'POST', body });
			const result: any = deserialize(await res.text());
			if (result.type === 'success' && result.data?.redirect) {
				if (result.data.resumed && result.data.ref_id) {
					resumedRef = result.data.ref_id;
				}
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
				action: item.kind === 'quickForm' ? '?/launchQuickForm' : '?/launchAssessment',
				showName: !!item.target.user_names,
				defaultName: item.title,
				showDomain: !item.target.folder
			}
		};
		const modal: ModalSettings = { type: 'component', component, title: item.title };
		modalStore.trigger(modal);
	}

	function trigger(item: PortalItem) {
		if (openPortalExternal(item)) return;
		if (item.kind === 'create' && item.target.model) openCreate(item.target.model, item.title);
		else if (item.kind === 'navigate' && item.target.model)
			breadcrumbGoto(`/${item.target.model}`, {
				label: URL_MODEL_MAP[item.target.model]?.localNamePlural ?? item.title,
				breadcrumbAction: 'replace'
			});
		else if (item.kind === 'assessment' || item.kind === 'quickForm') {
			// Launch directly only when nothing needs to be asked at click time.
			if (!item.target.folder || item.target.user_names) openLaunchModal(item);
			else launchAssessment(item);
		}
	}
</script>

{#if resumedRef}
	<aside class="card preset-tonal-primary mb-6 p-4 text-sm">
		<i class="fa-solid fa-rotate-left mr-2"></i>{m.quickFormResumedDraft({ ref: resumedRef })}
	</aside>
{/if}
{#if launchError}
	<aside class="card preset-tonal-error mb-6 p-4 text-sm">
		<i class="fa-solid fa-triangle-exclamation mr-2"></i>{launchError}
	</aside>
{/if}

<PortalGrid sections={data.portal?.sections ?? []} onTrigger={trigger} />
