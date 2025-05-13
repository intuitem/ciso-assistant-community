<script lang="ts">
	interface Props {
		value?: boolean;
		title?: string;
	}

	let { value = $bindable(false), title = 'Filter: ' }: Props = $props();
</script>

<div>
	<span style="margin-right: 0.25rem;">{title}</span>
	<!-- Styling must be done with tailwind -->
	<input class="checkbox" bind:checked={value} type="checkbox" />
</div>
