<script lang="ts">
	import Checkbox from '../Checkbox.svelte';
	import Select from '../Select.svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import type { CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperForm<any>;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
	}

	let { form, cacheLocks = {}, formDataCache = $bindable({}) }: Props = $props();

	const { value: level } = formFieldProxy(form, 'level');

	const levels = [
		{ label: m.read(), value: 'read' },
		{ label: m.create(), value: 'create' },
		{ label: m.update(), value: 'update' },
		{ label: m.approve(), value: 'approve' }
	];

	const levelHelp: Record<string, () => string> = {
		read: m.connectionProfileLevelRead,
		create: m.connectionProfileLevelCreate,
		update: m.connectionProfileLevelUpdate,
		approve: m.connectionProfileLevelApprove
	};
</script>

<Select
	{form}
	field="level"
	label={m.level()}
	options={levels}
	disableDoubleDash
	helpText={levelHelp[$level ?? 'read']?.()}
	cacheLock={cacheLocks['level']}
	bind:cachedValue={formDataCache['level']}
/>
<Checkbox
	{form}
	field="is_default"
	label={m.defaultProfile()}
	helpText={m.defaultProfileHelpText()}
	cacheLock={cacheLocks['is_default']}
	bind:cachedValue={formDataCache['is_default']}
/>
