<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { getModalStore } from '$lib/components/Modals/stores';
	import ApplyPresetModal from '$lib/components/Modals/ApplyPresetModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { goto } from '$lib/utils/breadcrumbs';
	import { page } from '$app/stores';

	let { data }: { data: PageData } = $props();

	const modalStore = getModalStore();

	const canApplyPreset = $derived(
		Object.hasOwn($page.data.user?.permissions ?? {}, 'add_loadedlibrary')
	);

	function startJourney() {
		modalStore.trigger({
			type: 'component',
			title: m.applyPreset(),
			body: m.applyPresetConfirm(),
			component: {
				ref: ApplyPresetModal,
				props: {
					presets: data.presets,
					domains: data.domains,
					onApply: async (payload: {
						preset_id?: string;
						folder_name?: string;
						folder_id?: string;
						create_objects?: boolean;
						apply_feature_flags?: boolean;
					}) => {
						try {
							const response = await fetch(`/presets/apply`, {
								method: 'POST',
								headers: { 'Content-Type': 'application/json' },
								body: JSON.stringify(payload)
							});
							if (response.ok) {
								const result = await response.json();
								goto(`/journeys/${result.journey_id}`, {
									label: result.journey_name,
									breadcrumbAction: 'push'
								});
								return { ok: true };
							}
							const err = await response.json().catch(() => ({}));
							const raw = err.error ?? err;
							let message: string;
							if (typeof raw === 'string') {
								message = raw;
							} else if (typeof raw === 'object') {
								message = Object.values(raw).flat().join(', ');
							} else {
								message = String(raw);
							}
							return { ok: false, error: message };
						} catch (e) {
							console.error('Failed to apply preset', e);
							return { ok: false, error: String(e) };
						}
					}
				}
			}
		});
	}
</script>

{#if data?.table}
	<div class="shadow-lg">
		<ModelTable
			source={data.table}
			deleteForm={data.deleteForm}
			URLModel="journeys"
			disableEdit={true}
		>
			{#snippet addButton()}
				{#if canApplyPreset && data.presets.length > 0}
					<div class="inline-flex overflow-hidden rounded-md border bg-surface-50-950 shadow-xs">
						<button
							class="inline-block p-3 btn-mini-primary w-12 focus:relative"
							data-testid="add-button"
							id="add-button"
							title={m.applyPreset()}
							aria-label={m.applyPreset()}
							onclick={startJourney}><i class="fa-solid fa-route"></i></button
						>
					</div>
				{/if}
			{/snippet}
		</ModelTable>
	</div>
{/if}
