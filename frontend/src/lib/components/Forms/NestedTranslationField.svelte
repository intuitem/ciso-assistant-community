<script lang="ts">
	import { m } from '$paraglide/messages';
	import { locales } from '$paraglide/runtime';
	import { LOCALE_MAP, language, defaultLangLabels } from '$lib/utils/locales';

	interface Subfield {
		key: string;
		label: string;
	}

	interface Props {
		/** {locale: {subfield: value}} — bound and mutated in place */
		value?: Record<string, Record<string, string>>;
		subfields: Subfield[];
		title?: string;
	}

	let { value = $bindable({}), subfields, title = m.translations() }: Props = $props();

	function addLocale() {
		const used = Object.keys(value ?? {});
		const next = (locales as readonly string[]).find((l) => !used.includes(l)) ?? locales[0];
		value = { ...value, [next]: {} };
	}

	function removeLocale(loc: string) {
		const copy = { ...value };
		delete copy[loc];
		value = copy;
	}

	function changeLocale(oldLoc: string, newLoc: string) {
		if (oldLoc === newLoc || value[newLoc]) return;
		const copy = { ...value };
		copy[newLoc] = copy[oldLoc] ?? {};
		delete copy[oldLoc];
		value = copy;
	}

	function setField(loc: string, key: string, v: string) {
		value = { ...value, [loc]: { ...value[loc], [key]: v } };
	}
</script>

<div class="space-y-2">
	<div class="flex items-center justify-between">
		<span class="text-sm font-semibold">{title}</span>
		<button
			type="button"
			class="btn btn-sm variant-soft-primary"
			onclick={addLocale}
			disabled={Object.keys(value ?? {}).length >= locales.length}
		>
			<i class="fa-solid fa-plus mr-1"></i>{m.addTranslation()}
		</button>
	</div>

	{#if Object.keys(value ?? {}).length === 0}
		<p class="text-sm text-surface-500 italic">{m.noTranslationAdded()}</p>
	{/if}

	{#each Object.entries(value ?? {}) as [loc, fields] (loc)}
		<div class="border rounded-container-token p-3 bg-surface-50 space-y-2">
			<div class="flex items-center justify-between gap-2">
				<select
					class="select w-auto text-sm"
					value={loc}
					onchange={(e) => changeLocale(loc, e.currentTarget.value)}
				>
					{#each locales as l}
						<option value={l}>{defaultLangLabels[l]} ({language[LOCALE_MAP[l].name]})</option>
					{/each}
				</select>
				<button
					type="button"
					class="btn-icon btn-icon-sm variant-soft-error"
					onclick={() => removeLocale(loc)}
					title={m.delete()}
				>
					<i class="fa-solid fa-trash"></i>
				</button>
			</div>
			{#each subfields as sub (sub.key)}
				<label class="block text-xs">
					{sub.label}
					<input
						type="text"
						class="input"
						value={fields?.[sub.key] ?? ''}
						oninput={(e) => setField(loc, sub.key, e.currentTarget.value)}
					/>
				</label>
			{/each}
		</div>
	{/each}
</div>
