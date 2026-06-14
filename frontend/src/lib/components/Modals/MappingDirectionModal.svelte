<script lang="ts">
	import { getModalStore, type ModalStore } from './stores';
	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		parent: any;
		/** Opens the "map to a framework" flow (create a new audit). */
		mapTo: () => void;
		/** Opens the "map from an audit" flow (update this audit). */
		mapFrom: () => void;
	}

	let { parent, mapTo, mapFrom }: Props = $props();

	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	function choose(action: () => void) {
		modalStore.close();
		action();
	}
</script>

{#if $modalStore[0]}
	<div class="modal-mapping-direction {cBase}">
		<div class="flex items-center justify-between">
			<header class={cHeader}>{m.applyMapping()}</header>
			<button
				type="button"
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<button
				class="flex flex-col items-start gap-2 p-4 rounded-xl border border-gray-200 bg-white text-left hover:bg-gray-50 hover:border-primary-400 transition-colors shadow-sm cursor-pointer"
				onclick={() => choose(mapTo)}
				data-testid="map-to-framework-card"
			>
				<i class="fa-solid fa-diagram-project text-emerald-500 text-2xl"></i>
				<span class="text-sm font-semibold">{m.mapToFramework()}</span>
				<span class="text-xs text-gray-500">{m.mapToFrameworkDescription()}</span>
			</button>
			<button
				class="flex flex-col items-start gap-2 p-4 rounded-xl border border-gray-200 bg-white text-left hover:bg-gray-50 hover:border-primary-400 transition-colors shadow-sm cursor-pointer"
				onclick={() => choose(mapFrom)}
				data-testid="map-from-audit-card"
			>
				<i class="fa-solid fa-arrow-right-to-bracket text-indigo-500 text-2xl"></i>
				<span class="text-sm font-semibold">{m.mapFromAudit()}</span>
				<span class="text-xs text-gray-500">{m.mapFromAuditDescription()}</span>
			</button>
		</div>
	</div>
{/if}
