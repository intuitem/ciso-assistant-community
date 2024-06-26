<script lang="ts">
	export let options: any[];
	export let value: string | undefined;
	export let defaultOptionName: string = '--';
	export let optionLabels: { [key: string]: string } = Object.fromEntries(
		options
			.filter(option => Boolean(option))
			.map((option) => [option, option.toString()])
	);
</script>

<!--
	data-testid="form-input-{field.replaceAll('_', '-')}"
	class="{'select ' + _class} {classesTextField($errors)}"
	aria-invalid={$errors ? 'true' : undefined}
	name={field}
-->

{#if Object.keys(optionLabels).length > 0}
	<select placeholder="" bind:value {...$$restProps}>
		<option value={null} selected>{defaultOptionName}</option>
		{#each options as option}
			{#if option}
				<option value={option}>
					{optionLabels[option]}
				</option>
			{/if}
		{/each}
	</select>
{/if}
