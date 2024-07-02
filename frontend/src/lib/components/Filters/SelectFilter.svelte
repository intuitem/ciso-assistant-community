<script lang="ts">
	export let options: any[];
	export let value: string | undefined;
	export let defaultOptionName: string = '--';
	export let optionLabels: { [key: string]: string } = {};
</script>

{#if options.length > 0}
	<!-- I should use class="m-0" instead of style="margin: 0;" but i didn't figure out to make tailwind add this class yet -->
	<select class="input bg-surface-50 max-w-2xl" placeholder="" bind:value {...$$restProps} style="margin: 0;">
		<option value={null} selected>{defaultOptionName}</option>
		{#each options as option}
			{#if option}
				{@const label = optionLabels[option] ?? option}
				<option value={option}>
					{label}
				</option>
			{/if}
		{/each}
	</select>
{/if}
