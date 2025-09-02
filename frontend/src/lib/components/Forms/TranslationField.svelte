<script lang="ts">
	import { m } from '$paraglide/messages';
	import { onMount } from 'svelte';
	import type { CacheLock } from '$lib/utils/types';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import { locales } from '$paraglide/runtime';
	import { LOCALE_MAP, language, defaultLangLabels } from '$lib/utils/locales';

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

	let translations: Record<string, string> = $state(cachedValue || initialValue);

	onMount(async () => {
		const cacheResult = await cacheLock.promise;
		if (cacheResult) $value = cacheResult;
	});

	function addTranslation() {
		const used = Object.keys(translations);
		const available = locales.find((l) => !used.includes(l));
		console.log({ used, available });
		const newCode = available || 'en';
		translations = { ...translations, [newCode]: '' };
	}

	let availableLanguages = $state(() => {
		const used = Object.keys(translations);
		return locales.filter((l) => !used.includes(l));
	});

	function removeTranslation(lang: string) {
		const copy = { ...translations };
		delete copy[lang];
		translations = copy;
	}

	function updateLanguageKey(oldLang: string, newLang: string) {
		if (oldLang === newLang) return;

		const copy = { ...translations };
		const value = copy[oldLang] || '';

		// Remove old key
		delete copy[oldLang];

		// Add with new key if it doesn't already exist
		if (!copy[newLang]) {
			copy[newLang] = value;
		}

		translations = copy;
	}

	function updateTranslationValue(lang: string, value: string) {
		translations = { ...translations, [lang]: value };
	}

	// Keep cachedValue synced with translations
	$effect(() => {
		if (cachedValue !== translations) {
			cachedValue = translations;
		}

		// Update form data if form exists
		if (form.data) {
			form.data.translations = translations;
		}
	});
</script>

<div class="space-y-4">
	<div class="flex items-center justify-between">
		<label class="text-sm font-semibold">{m.translations()}</label>
		<button
			type="button"
			class="px-3 py-1 text-sm rounded bg-blue-100 hover:bg-blue-200 text-blue-700 transition-colors"
			onclick={() => addTranslation()}
			disabled={Object.keys(translations).length >= locales.length}
		>
			<i class="fa-solid fa-plus mr-1"></i>{m.addTranslation()}
		</button>
	</div>

	{#if Object.keys(translations).length === 0}
		<div
			class="text-gray-500 text-sm italic text-center py-4 border-2 border-dashed border-gray-200 rounded"
		>
			{m.noTranslationAdded()}
		</div>
	{/if}

	<div class="space-y-3">
		{#each Object.entries(translations) as [lang, text], i (i + '-' + lang)}
			<div class="flex gap-2 items-start p-3 bg-gray-50 rounded-lg">
				<div class="flex-1">
					{#if $errors && $errors[lang]}
						<div class="text-xs text-red-500 mb-1">{m.translationErrorMessage()}</div>
					{/if}
					<label class="block text-xs font-medium text-gray-600 mb-1">{m.language()}</label>
					<select
						value={lang}
						onchange={(e) => updateLanguageKey(lang, e.target.value)}
						class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					>
						<option value="">{m.selectLanguagePlaceholder()}</option>
						{#each locales as lang}
							<option value={lang}>
								{defaultLangLabels[lang]} ({language[LOCALE_MAP[lang].name]})
							</option>
						{/each}
					</select>
				</div>

				<div class="flex-[2]">
					{#if $errors && $errors[lang]}
						<div class="text-xs text-red-500 mb-1 invisible">{m.translationErrorMessage()}</div>
					{/if}
					<label class="block text-xs font-medium text-gray-600 mb-1">{m.translations()}</label>
					<input
						type="text"
						value={text}
						oninput={(e) => updateTranslationValue(lang, e.target.value)}
						placeholder="Enter translation..."
						class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>

				<div class="pt-6">
					<button
						type="button"
						class="text-red-600 hover:text-red-800 hover:bg-red-50 p-1 rounded transition-colors"
						onclick={() => removeTranslation(lang)}
						title="Remove translation"
					>
						✕
					</button>
				</div>
			</div>

			<!-- Hidden input to ensure form data is submitted -->
			<input type="hidden" name="translations[{lang}]" value={text} />
		{/each}
	</div>

	<!-- Hidden input for the entire translations object as JSON -->
	<input type="hidden" name="translations" value={JSON.stringify(translations)} />
</div>

<style>
	.space-y-2 > * + * {
		margin-top: 0.5rem;
	}

	.space-y-3 > * + * {
		margin-top: 0.75rem;
	}

	.space-y-4 > * + * {
		margin-top: 1rem;
	}
</style>
