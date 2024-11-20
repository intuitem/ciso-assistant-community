<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import { onMount } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	let _class = '';
	export { _class as class };
	export let label: string | undefined = undefined;
	export let field: string;
	export let valuePath = field; // the place where the value is stored in the form. This is useful for nested objects
	export let helpText: string | undefined = undefined;
	export let cachedValue: number | undefined;
	export let cacheLock: CacheLock = {
		promise: new Promise((res) => res(null)),
		resolve: (x) => x
	};
	export let form: SuperForm<Record<string, number>>;
	export let hidden = false;
	export let disabled = false;
	export let required = false;

	label = label ?? field;
	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	interface TimeUnit {
		unit: string;
		secondsMultiplier: number;
		enabled: boolean;
		value: number;
	}

	const _timeUnits: TimeUnit[] = [
		{ unit: 'days', secondsMultiplier: 86400, enabled: false, value: 0 },
		{ unit: 'hours', secondsMultiplier: 3600, enabled: true, value: 0 },
		{ unit: 'minutes', secondsMultiplier: 60, enabled: true, value: 0 },
		{ unit: 'seconds', secondsMultiplier: 1, enabled: true, value: 0 },
		{ unit: 'milliseconds', secondsMultiplier: 0.001, enabled: false, value: 0 }
	];

	function setInitialTimeUnitValues(value: number, units: TimeUnit[]): TimeUnit[] {
		let remainingValue = value;
		units.forEach((timeUnit) => {
			if (timeUnit.enabled) {
				timeUnit.value = Math.floor(remainingValue / timeUnit.secondsMultiplier);
				remainingValue = remainingValue % timeUnit.secondsMultiplier;
			}
		});
		return units;
	}

	const timeUnits = setInitialTimeUnitValues($value || 0, _timeUnits);

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	$: classesTextField = (errors: string[] | undefined) => (errors ? 'input-error' : '');
	$: classesDisabled = (d: boolean) => (d ? 'opacity-50' : '');
	$: $value = timeUnits.reduce((acc, timeUnit) => {
		return timeUnit.enabled ? acc + timeUnit.value * timeUnit.secondsMultiplier : acc;
	}, 0);
	$: cachedValue = $value;
</script>

<div>
	<div class={classesDisabled(disabled)}>
		{#if label !== undefined && !hidden}
			{#if $constraints?.required || required}
				<label class="text-sm font-semibold" for={field}
					>{label} <span class="text-red-500">*</span></label
				>
			{:else}
				<label class="text-sm font-semibold" for={field}>{label}</label>
			{/if}
		{/if}
		{#if $errors}
			<div>
				{#each $errors as error}
					<p class="text-error-500 text-xs font-medium">{error}</p>
				{/each}
			</div>
		{/if}
	</div>
	<div class="control flex flex-row space-x-2">
		{#each timeUnits as timeUnit}
			{#if timeUnit.enabled}
				<div>
					<label class="text-sm" for={field}>{safeTranslate(timeUnit.unit)}</label>
					<input
						type="number"
						class="{'input ' + _class} {classesTextField($errors)}"
						data-testid="form-input-{field.replaceAll('_', '-')}"
						name={field}
						aria-invalid={$errors ? 'true' : undefined}
						placeholder=""
						bind:value={timeUnit.value}
						{disabled}
						{required}
						{...$constraints}
						{...$$restProps}
					/>
				</div>
			{/if}
		{/each}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
