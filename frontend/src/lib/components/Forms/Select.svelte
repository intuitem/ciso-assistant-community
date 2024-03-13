<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms/client';
	import { localItems, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';
	import type { AnyZodObject } from 'zod';

	let _class = '';

	export { _class as class };
	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;
	export let origin: string = "default";

	export let color_map = {};

	export let form: SuperForm<AnyZodObject>;

	const { value, errors, constraints } = formFieldProxy(form, field);

	interface Option {
		label: unknown;
		value: unknown;
	}

	export let options: Option[];

	$: classesTextField = (errors: string[] | undefined) =>
		errors && errors.length > 0 ? 'input-error' : '';

	const hasBlankField = !$constraints?.required && !options.find((o) => o.label === '--');
	let defaultOption: Element | null = null;

	$: if (defaultOption && origin === "default") { defaultOption.setAttribute("selected","true"); }
</script>

<div>
	{#if label !== undefined}
		{#if $constraints?.required}
			<label class="text-sm font-semibold" for={field}
				>{label} <span class="text-red-500">*</span></label
			>
		{:else}
			<label class="text-sm font-semibold" for={field}>{label}</label>
		{/if}
	{/if}
	{#if $errors && $errors.length > 0}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div class="control">
		<select
			class="{'select ' + _class} {classesTextField($errors)}"
			data-testid="form-input-{field.replaceAll('_', '-')}"
			name={field}
			aria-invalid={$errors ? 'true' : undefined}
			placeholder=""
			style="background-color: {color_map[$value]}"
			bind:value={$value}
			{...$constraints}
			{...$$restProps}
		>
			{#if hasBlankField}
				<option value={null} selected>--</option>
			{/if}

			{#each options as option, index}
				<!-- The legend has it that one day Svelte 5 snippets will clean this horrible code repetition. -->
				{#if index === 0 && !hasBlankField}
					<option
						value={option.value}
						style="background-color: {color_map[option.value]}"
						bind:this={defaultOption}
					>
						{#if localItems(languageTag())[toCamelCase(option.label)]}
							{localItems(languageTag())[toCamelCase(option.label)]}
						{:else}
							{option.label}
						{/if}
					</option>
				{:else}
					<option
						value={option.value}
						style="background-color: {color_map[option.value]}"
					>
						{#if localItems(languageTag())[toCamelCase(option.label)]}
							{localItems(languageTag())[toCamelCase(option.label)]}
						{:else}
							{option.label}
						{/if}
					</option>
				{/if}
			{/each}
		</select>
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
