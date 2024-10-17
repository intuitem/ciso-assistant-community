<script lang="ts">
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { availableLanguageTags } from '$paraglide/runtime';
	import { LOCALE_DISPLAY_MAP } from '$lib/utils/constants';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let data: any = {};

	const langOptions = availableLanguageTags.map((lang) => {
		return {
			label: LOCALE_DISPLAY_MAP[lang] ?? '[Unknown Language]',
			value: lang
		};
	});
</script>

<Select
	{form}
	field="lang"
	cacheLock={cacheLocks['lang']}
	bind:cachedValue={formDataCache['lang']}
	options={langOptions}
	label={m.defaultLanguage()}
/>
