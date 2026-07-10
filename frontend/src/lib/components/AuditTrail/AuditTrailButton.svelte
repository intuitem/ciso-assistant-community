<script lang="ts">
	// Community stub. The per-object audit trail is an enterprise feature;
	// enterprise/frontend overlays this file with the real implementation.
	interface Props {
		model?: string;
		objectId?: string;
	}

	let { model, objectId }: Props = $props();
	void model;
	void objectId;
</script>
