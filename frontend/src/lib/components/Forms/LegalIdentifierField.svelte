<script lang="ts">
	import { m } from '$paraglide/messages';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	interface Props {
		form: SuperForm<Record<string, unknown>, any>;
		field: string;
		cacheLock?: CacheLock;
		cachedValue?: any[] | undefined;
	}

	let {
		form,
		field,
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x: any) => x
		},
		cachedValue = $bindable()
	}: Props = $props();

	const { value, errors, constraints } = formFieldProxy(form, field);

	const initialValue = $state($value || {});

	$effect(() => {
		$value = cachedValue;
	});

	let legalIdentifiers: Record<string, string> = $state(cachedValue || initialValue);

	const identifierTypes = [
		{ value: 'LEI', label: 'LEI (Legal Entity Identifier)' },
		{ value: 'EUID', label: 'EUID (European Unique Identifier)' },
		{ value: 'DUNS', label: 'DUNS Number' },
		{ value: 'VAT', label: 'VAT Number' },
		{ value: 'OTHER', label: 'Other' }
	];

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	function addIdentifier() {
		const used = Object.keys(legalIdentifiers);
		const available = identifierTypes.find((t) => !used.includes(t.value));
		const newType = available?.value || 'OTHER';
		legalIdentifiers = { ...legalIdentifiers, [newType]: '' };
	}

	function removeIdentifier(type: string) {
		const copy = { ...legalIdentifiers };
		delete copy[type];
		legalIdentifiers = copy;
	}

	function updateIdentifierType(oldType: string, newType: string) {
		if (oldType === newType) return;

		const copy = { ...legalIdentifiers };
		const value = copy[oldType] || '';

		// Remove old key
		delete copy[oldType];

		// Add with new key if it doesn't already exist
		if (!copy[newType]) {
			copy[newType] = value;
		}

		legalIdentifiers = copy;
	}

	function updateIdentifierValue(type: string, value: string) {
		legalIdentifiers = { ...legalIdentifiers, [type]: value };
	}

	// Keep cachedValue synced with legalIdentifiers
	$effect(() => {
		if (cachedValue !== legalIdentifiers) {
			cachedValue = legalIdentifiers;
		}

		// Update form data if form exists
		if (form.data) {
			form.data.legal_identifiers = legalIdentifiers;
		}
	});
</script>

<div class="space-y-4">
	<div class="flex items-center justify-between">
		<span class="text-sm font-semibold">{m.legalIdentifiers()}</span>
		<button
			type="button"
			class="px-3 py-1 text-sm rounded bg-blue-100 hover:bg-blue-200 text-blue-700 transition-colors"
			onclick={() => addIdentifier()}
			disabled={Object.keys(legalIdentifiers).length >= identifierTypes.length}
		>
			<i class="fa-solid fa-plus mr-1"></i>{m.addLegalIdentifier()}
		</button>
	</div>

	<!-- Display field-level errors -->
	{#if $errors && !Array.isArray($errors) && typeof $errors === 'string'}
		<div class="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
			{m[$errors] || $errors}
		</div>
	{:else if $errors && Array.isArray($errors) && $errors.length > 0}
		<div class="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
			{#each $errors as error}
				<div>{m[error] || error}</div>
			{/each}
		</div>
	{/if}

	{#if Object.keys(legalIdentifiers).length === 0}
		<div
			class="text-gray-500 text-sm italic text-center py-4 border-2 border-dashed border-gray-200 rounded"
		>
			{m.noLegalIdentifierAdded()}
		</div>
	{/if}

	<div class="space-y-3">
		{#each Object.entries(legalIdentifiers) as [type, identifier], i (i + '-' + type)}
			<div class="flex gap-2 items-start p-3 bg-gray-50 rounded-lg">
				<div class="flex-1">
					{#if $errors && $errors[type]}
						<div class="text-xs text-red-500 mb-1">{m.identifierErrorMessage()}</div>
					{/if}
					<label for="identifier-type-{i}" class="block text-xs font-medium text-gray-600 mb-1"
						>{m.identifierType()}</label
					>
					<select
						id="identifier-type-{i}"
						value={type}
						onchange={(e) => updateIdentifierType(type, e.target.value)}
						class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					>
						{#each identifierTypes as idType}
							<option value={idType.value}>
								{idType.label}
							</option>
						{/each}
					</select>
				</div>

				<div class="flex-[2]">
					{#if $errors && $errors[type]}
						<div class="text-xs text-red-500 mb-1 invisible">{m.identifierErrorMessage()}</div>
					{/if}
					<label for="identifier-value-{i}" class="block text-xs font-medium text-gray-600 mb-1"
						>{m.identifierValue()}</label
					>
					<input
						id="identifier-value-{i}"
						type="text"
						value={identifier}
						oninput={(e) => updateIdentifierValue(type, e.target.value)}
						placeholder={m.enterIdentifierValue()}
						class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>

				<div class="pt-6">
					<button
						type="button"
						class="text-red-600 hover:text-red-800 hover:bg-red-50 p-1 rounded transition-colors"
						onclick={() => removeIdentifier(type)}
						title={m.removeIdentifier()}
						aria-label={m.removeIdentifier()}
					>
						<i class="fa-solid fa-trash"></i>
					</button>
				</div>
			</div>

			<!-- Hidden input to ensure form data is submitted -->
			<input type="hidden" name="legal_identifiers[{type}]" value={identifier} />
		{/each}
	</div>

	<!-- Hidden input for the entire legal_identifiers object as JSON -->
	<input type="hidden" name="legal_identifiers" value={JSON.stringify(legalIdentifiers)} />
</div>

<style>
	.space-y-3 > * + * {
		margin-top: 0.75rem;
	}

	.space-y-4 > * + * {
		margin-top: 1rem;
	}
</style>
