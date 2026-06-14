<script lang="ts">
	import { goto } from '$app/navigation';
	import AutocompleteSelect from '../Forms/AutocompleteSelect.svelte';
	import { getModalStore, type ModalStore } from './stores';
	import { superForm } from 'sveltekit-superforms';
	import { z } from 'zod';
	import { m } from '$paraglide/messages';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		parent: any;
		currentAudit: {
			id: string;
			framework: { id: string };
		};
	}

	let { parent, currentAudit }: Props = $props();

	const cBase = 'card bg-surface-50 p-4 w-fit max-w-2xl shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	const schema = z.object({
		source_audit: z.string().uuid().optional()
	});

	let checking = $state(false);
	let errorMessage = $state('');

	const form = superForm(
		{ source_audit: undefined },
		{
			validators: zod(schema),
			SPA: true,
			onSubmit: async ({ cancel }) => {
				// Always handled manually below; never let superForm POST.
				cancel();
				const selectedAuditId = $formData.source_audit;
				if (!selectedAuditId || checking) return;

				// Preflight: confirm a mapping path exists before navigating, so a
				// "no mapping path" error surfaces here in the form rather than as a
				// full-page error on the preview route.
				checking = true;
				errorMessage = '';
				try {
					const res = await fetch(
						`/compliance-assessments/${currentAudit.id}/map-from?source_audit_id=${selectedAuditId}`
					);
					if (res.ok) {
						goto(
							`/compliance-assessments/map-from-preview?target=${currentAudit.id}&source=${selectedAuditId}`
						);
						modalStore.close();
					} else if (res.status === 400) {
						// The only 400 from this endpoint is a missing mapping path.
						errorMessage = m.noMappingPath();
					} else {
						const body = await res.json().catch(() => ({}));
						errorMessage = body?.error || m.mapFromError();
					}
				} catch {
					errorMessage = m.mapFromError();
				} finally {
					checking = false;
				}
			}
		}
	);

	const { form: formData, enhance } = form;
</script>

{#if $modalStore[0]}
	<div class="modal-map-from-audit {cBase}">
		<div class="flex items-center justify-between">
			<header class={cHeader} data-testid="modal-title">{m.mapFromAudit()}</header>
			<button
				type="button"
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</div>
		<form method="POST" use:enhance class="space-y-4">
			<AutocompleteSelect
				{form}
				field="source_audit"
				label={m.selectSourceAudit()}
				optionsEndpoint="compliance-assessments"
				optionsSelf={{ id: currentAudit.id }}
				optionsLabelField="auto"
				optionsExtraFields={[['folder', 'str']]}
				optionsInfoFields={{
					fields: [
						{ field: 'framework', path: 'str', translate: false },
						{ field: 'version', translate: false },
						{ field: 'perimeter', path: 'str', translate: false },
						{ field: 'status', translate: true }
					],
					position: 'suffix',
					separator: ' • ',
					classes: 'text-surface-500'
				}}
				onChange={() => {
					errorMessage = '';
				}}
			/>
			{#if errorMessage}
				<div
					class="rounded-md border border-error-300 bg-error-50 px-3 py-2 text-sm text-error-700"
					role="alert"
				>
					<i class="fa-solid fa-triangle-exclamation mr-1"></i>
					{errorMessage}
				</div>
			{/if}
			<div class="flex justify-end space-x-2">
				<button type="button" class="btn preset-filled-surface-500" onclick={parent.onClose}>
					{m.cancel()}
				</button>
				<button
					type="submit"
					class="btn preset-filled-primary-500"
					disabled={!$formData.source_audit || checking}
					data-testid="map-from-submit-button"
				>
					{#if checking}
						<i class="fa-solid fa-spinner fa-spin mr-2"></i>
					{:else}
						<i class="fa-solid fa-arrow-right-to-bracket mr-2"></i>
					{/if}
					{m.mapFromAudit()}
				</button>
			</div>
		</form>
	</div>
{/if}
