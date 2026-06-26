<script lang="ts" module>
	// Fetched once and shared across all instances.
	let auditedModelsPromise: Promise<Set<string>> | null = null;

	function loadAuditedModels(fetchFn: typeof fetch): Promise<Set<string>> {
		if (!auditedModelsPromise) {
			auditedModelsPromise = fetchFn('/fe-api/audited-models')
				.then((res) => {
					if (!res.ok) throw new Error(`HTTP ${res.status}`);
					return res.json();
				})
				.then((names: string[]) => new Set(names))
				.catch(() => {
					// Don't cache transient failures: reset so the next mount retries.
					auditedModelsPromise = null;
					return new Set<string>();
				});
		}
		return auditedModelsPromise;
	}
</script>

<script lang="ts">
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import type { urlModel } from '$lib/utils/types';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import AuditTrailModal from '$lib/components/AuditTrail/AuditTrailModal.svelte';
	import { onMount } from 'svelte';

	interface Props {
		model?: string;
		objectId?: string;
	}

	let { model = '', objectId = '' }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	const contentType = $derived(URL_MODEL_MAP[model as urlModel]?.name ?? '');

	let auditedModels: Set<string> = $state(new Set());
	onMount(async () => {
		auditedModels = await loadAuditedModels(fetch);
	});

	const hasPermission = $derived(!!page.data?.user?.permissions?.view_object_audittrail);
	const featureEnabled = $derived(page.data?.featureflags?.object_audit_trail !== false);

	const enabled = $derived(
		featureEnabled && hasPermission && !!contentType && !!objectId && auditedModels.has(contentType)
	);

	function openAuditTrail() {
		const modalComponent: ModalComponent = {
			ref: AuditTrailModal,
			props: { model: contentType, objectId }
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.auditTrail()
		};
		modalStore.trigger(modal);
	}
</script>

{#if enabled}
	<button
		type="button"
		class="btn h-fit text-gray-100 bg-linear-to-l from-slate-500 to-slate-700"
		data-testid="audit-trail-button"
		onclick={openAuditTrail}
	>
		<i class="fa-solid fa-clock-rotate-left mr-2"></i>
		{m.auditTrail()}
	</button>
{/if}
