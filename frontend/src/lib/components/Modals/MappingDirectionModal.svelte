<script lang="ts">
	import ChoiceCardsModal from './ChoiceCardsModal.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		parent: any;
		/** Opens the "map to a framework" flow (create a new audit). */
		mapTo: () => void;
		/** Opens the "map from an audit" flow (update this audit). */
		mapFrom: () => void;
	}

	let { parent, mapTo, mapFrom }: Props = $props();

	const choices = [
		{
			icon: 'fa-diagram-project',
			iconClass: 'text-emerald-500',
			label: m.mapToFramework(),
			description: m.mapToFrameworkDescription(),
			testId: 'map-to-framework-card',
			action: mapTo
		},
		{
			icon: 'fa-arrow-right-to-bracket',
			iconClass: 'text-indigo-500',
			label: m.mapFromAudit(),
			description: m.mapFromAuditDescription(),
			testId: 'map-from-audit-card',
			action: mapFrom
		}
	];
</script>

<ChoiceCardsModal {parent} title={m.applyMapping()} {choices} />
