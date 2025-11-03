<script lang="ts">
	import { goto } from '$app/navigation';
	import AutocompleteSelect from '../Forms/AutocompleteSelect.svelte';
	import { getModalStore, type ModalStore } from './stores';
	import { superForm } from 'sveltekit-superforms';
	import { z } from 'zod';
	import { m } from '$paraglide/messages';
	import { zod } from 'sveltekit-superforms/adapters';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		parent: any;
		currentAudit: {
			id: string;
			framework: { id: string };
			perimeter?: { id: string };
		};
	}

	let { parent, currentAudit }: Props = $props();

	const cBase = 'card bg-surface-50 p-4 w-fit max-w-2xl shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	// Create a simple form schema for the comparison selection
	const schema = z.object({
		comparison_audit: z.string().uuid().optional()
	});

	const form = superForm(
		{ comparison_audit: undefined },
		{
			validators: zod(schema),
			SPA: true,
			onSubmit: () => {
				const selectedAuditId = $formData.comparison_audit;
				if (selectedAuditId) {
					// Redirect to comparison page
					goto(
						`/compliance-assessments/compare?base=${currentAudit.id}&compare=${selectedAuditId}`
					);
					modalStore.close();
				}
			}
		}
	);

	const { form: formData, enhance } = form;

	// Use the proxied comparable_audits endpoint (AutocompleteSelect will add leading slash)
	const comparableAuditsEndpoint = `compliance-assessments/${currentAudit.id}/comparable_audits`;
</script>

{#if $modalStore[0]}
	<div class="modal-compare-audit {cBase}">
		<div class="flex items-center justify-between">
			<header class={cHeader}>{m.compareToAudit()}</header>
			<div
				role="button"
				tabindex="0"
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
				onkeydown={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</div>
		</div>
		<form method="POST" use:enhance class="space-y-4">
			<AutocompleteSelect
				{form}
				field="comparison_audit"
				label={m.selectAuditToCompare()}
				optionsEndpoint={comparableAuditsEndpoint}
				optionsLabelField="auto"
				optionsInfoFields={{
					fields: [
						{ field: 'version', translate: true },
						{ field: 'perimeter', path: 'str', translate: false },
						{ field: 'status', translate: true }
					],
					position: 'suffix',
					separator: ' • ',
					classes: 'text-surface-500'
				}}
				helpText={m.auditsWithSameFrameworkPrioritized()}
				onChange={() => {}}
			/>
			<div class="flex justify-end space-x-2">
				<button type="button" class="btn preset-filled-surface-500" onclick={parent.onClose}>
					{m.cancel()}
				</button>
				<button
					type="submit"
					class="btn preset-filled-primary-500"
					disabled={!$formData.comparison_audit}
				>
					<i class="fa-solid fa-code-compare mr-2"></i>
					{m.compareToAudit()}
				</button>
			</div>
		</form>
	</div>
{/if}
