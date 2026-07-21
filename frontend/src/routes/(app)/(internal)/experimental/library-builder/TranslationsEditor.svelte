<script lang="ts">
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP, language } from '$lib/utils/locales';

	interface Field {
		key: string;
		label: string;
		textarea?: boolean;
	}

	interface Props {
		/** {lang: {field: value}} — bound; mutations go through replacement. */
		translations: Record<string, Record<string, string>>;
		fields: Field[];
		/** The document's base locale: excluded from the language choices. */
		baseLang: string;
		onchange?: () => void;
	}

	let { translations = $bindable(), fields, baseLang, onchange }: Props = $props();

	let langs = $derived(Object.keys(translations ?? {}).filter((code) => code !== baseLang));

	let availableToAdd = $derived(
		Object.entries(LOCALE_MAP)
			.filter(([code]) => code !== baseLang && !(code in (translations ?? {})))
			.map(([code, info]) => ({ code, name: language[info.name] ?? info.name }))
	);

	function localeLabel(code: string): string {
		return language[LOCALE_MAP[code as keyof typeof LOCALE_MAP]?.name] ?? code;
	}

	function addLanguage(code: string) {
		translations = { ...(translations ?? {}), [code]: {} };
		onchange?.();
	}

	function removeLanguage(code: string) {
		const { [code]: _removed, ...rest } = translations ?? {};
		translations = rest;
		onchange?.();
	}

	function setValue(code: string, field: string, value: string) {
		const current = translations?.[code] ?? {};
		translations = { ...(translations ?? {}), [code]: { ...current, [field]: value } };
		onchange?.();
	}
</script>

<div class="space-y-2">
	<div class="flex items-center gap-2 flex-wrap">
		<span class="text-xs font-medium text-surface-600-400">
			<i class="fa-solid fa-language mr-1" aria-hidden="true"></i>{m.translations()}
		</span>
		{#if availableToAdd.length > 0}
			<select
				class="select select-sm w-36 text-xs"
				onchange={(e) => {
					const value = e.currentTarget.value;
					if (value) addLanguage(value);
					e.currentTarget.value = '';
				}}
			>
				<option value="">+ {m.addLanguage()}</option>
				{#each availableToAdd as lang}
					<option value={lang.code}>{lang.name}</option>
				{/each}
			</select>
		{/if}
	</div>
	{#each langs as code (code)}
		<div class="border border-surface-200-800 rounded p-2 space-y-2">
			<div class="flex items-center justify-between">
				<span class="text-xs font-semibold">
					{localeLabel(code)}
					<span class="opacity-60">({code})</span>
				</span>
				<button
					type="button"
					class="text-surface-400 hover:text-red-500 transition-colors"
					onclick={() => {
						if (confirm(m.removeLanguageConfirm({ lang: localeLabel(code) }))) {
							removeLanguage(code);
						}
					}}
					aria-label="{m.removeLanguageConfirm({ lang: localeLabel(code) })} ({code})"
				>
					<i class="fa-solid fa-xmark text-xs" aria-hidden="true"></i>
				</button>
			</div>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
				{#each fields as field (field.key)}
					<label class="label text-xs {field.textarea ? 'md:col-span-2' : ''}">
						<span>{field.label} <span class="opacity-60">({code})</span></span>
						{#if field.textarea}
							<textarea
								class="textarea text-sm"
								rows="2"
								value={translations?.[code]?.[field.key] ?? ''}
								oninput={(e) => setValue(code, field.key, e.currentTarget.value)}
							></textarea>
						{:else}
							<input
								class="input text-sm"
								type="text"
								value={translations?.[code]?.[field.key] ?? ''}
								oninput={(e) => setValue(code, field.key, e.currentTarget.value)}
							/>
						{/if}
					</label>
				{/each}
			</div>
		</div>
	{/each}
</div>
