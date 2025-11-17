<script lang="ts">
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	interface Option {
		label: string;
		value: string;
	}

	interface Props {
		label?: string | undefined;
		field: string;
		valuePath?: any; // the place where the value is stored in the form. This is useful for nested objects
		helpText?: string | undefined;
		options?: Option[];
		cachedValue?: string[] | undefined;
		form: SuperForm<Record<string, any | undefined>>;
		hidden?: boolean;
		disabled?: boolean;
		classes?: string;
		classesContainer?: string;
		[key: string]: any;
	}

	let {
		label = $bindable(),
		field,
		valuePath = field,
		helpText = undefined,
		options = [],
		cachedValue = $bindable(),
		form,
		hidden = false,
		disabled = false,
		classes = '',
		classesContainer = '',
		...rest
	}: Props = $props();

	label = label ?? field;

	const { value, errors, constraints } = formFieldProxy(form, valuePath);
	$effect(() => {
		cachedValue = $value;
	});

	let classesHidden = $derived((h: boolean) => (h ? 'hidden' : ''));
	let classesDisabled = $derived((d: boolean) => (d ? 'opacity-50' : ''));
</script>

{#if options}
	{#each options as option}
		<div class="flex items-center mb-2 {classes} {classesDisabled(disabled)}">
			<input
				type="checkbox"
				id={option.value}
				value={option.value}
				checked={$value.includes(option.value)}
				{disabled}
				onchange={(e: Event) => {
					let newValue: string[] = [...$value];
					if ((e.target as HTMLInputElement).checked) {
						newValue.push(option.value);
					} else {
						newValue = newValue.filter((v) => v !== option.value);
					}
					$value = newValue;
				}}
				class="mr-2"
			/>
			<label for={option.value}>{option.label}</label>
		</div>
	{:else}
		<LoadingSpinner />
	{/each}
{/if}
