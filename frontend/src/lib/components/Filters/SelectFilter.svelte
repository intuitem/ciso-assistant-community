<script lang="ts">
	export let options: any[];
	export let value: string | undefined;
	export let defaultOptionName: string = "--";
	export let OptionLabels: {[key: string]: string} = Object.fromEntries(
		options.map(option => [option,option.toString()])
	);
</script>

<!--
	data-testid="form-input-{field.replaceAll('_', '-')}"
	class="{'select ' + _class} {classesTextField($errors)}"
	aria-invalid={$errors ? 'true' : undefined}
	name={field}
-->

<select
	placeholder=""
	bind:value={value}
	{...$$restProps}
>
	<option value={null} selected>{defaultOptionName}</option>
	{#each options as option}
		{#if option}
			<option value={option}>
				{OptionLabels[option]}
			</option>
		{/if}
	{/each}
</select>
