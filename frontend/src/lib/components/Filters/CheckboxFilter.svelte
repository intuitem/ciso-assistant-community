<script lang="ts">
	export let options: any[];
	export let value: boolean = false;
	export let title: string = 'Filter: ';
</script>

<div>
	<span style="margin-right: 0.25rem;">{title}</span>
	<!-- Styling must be done with tailwind -->
	<input class="checkbox" bind:checked={value} type="checkbox" />
</div>
