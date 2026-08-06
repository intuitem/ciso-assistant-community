<script lang="ts">
	import FilterNameModal from './FilterNameModal.svelte';

	interface Props {
		parent: any;
		initialName: string;
		onRenamed: (name: string) => void;
	}

	let { parent, initialName, onRenamed }: Props = $props();
</script>

<FilterNameModal {parent} {initialName} onSubmit={(name) => onRenamed(name)} />
