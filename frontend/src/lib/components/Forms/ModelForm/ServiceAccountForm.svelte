<script lang="ts">
	import { onMount } from 'svelte';
	import { formFieldProxy } from 'sveltekit-superforms';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Checkbox from '../Checkbox.svelte';
	import ListSelector from '../ListSelector.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperForm<any, any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		shape?: any;
		context?: string;
		object?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		shape = {},
		context,
		object = {}
	}: Props = $props();

	interface BuiltinRole {
		id: string;
		name: string;
		permissions: number[];
	}

	let builtinRoles: BuiltinRole[] = $state([]);
	let permissionsSelector: ReturnType<typeof ListSelector> | undefined = $state();

	const { value: roleValue } = formFieldProxy(form, 'role');
	const { value: permissionsValue } = formFieldProxy(form, 'permissions');

	const isEditingRoleLinked = context === 'edit' && Boolean(object.is_role_linked);
	let mode: 'role' | 'custom' = $state(isEditingRoleLinked ? 'role' : 'custom');
	let customPermissions: number[] = $state(
		!isEditingRoleLinked && Array.isArray(object.permissions) ? object.permissions : []
	);

	let selectedRoleId: string = $state(typeof object.role === 'string' ? object.role : '');

	setAuthorizationFields(mode);

	onMount(async () => {
		const res = await fetch('/service-accounts/roles');
		if (res.ok) builtinRoles = await res.json();
	});

	function setAuthorizationFields(next: 'role' | 'custom'): void {
		form.form.update((data) => {
			const updated = { ...data };
			updated.authorization_mode = next;
			if (next === 'role') {
				delete updated.permissions;
				if (selectedRoleId) updated.role = selectedRoleId;
				else delete updated.role;
			} else {
				delete updated.role;
				updated.permissions = customPermissions;
			}
			return updated;
		});
	}

	function selectMode(next: 'role' | 'custom'): void {
		if (next === mode) return;

		if (mode === 'custom') {
			customPermissions = Array.isArray($permissionsValue)
				? $permissionsValue.filter(
						(permission): permission is number => typeof permission === 'number'
					)
				: [];
		}

		mode = next;
		formDataCache['permissions'] = customPermissions;
		setAuthorizationFields(next);
	}

	function pickRole(roleId: string): void {
		selectedRoleId = roleId;
		$roleValue = roleId || undefined;
	}

	function applyRolePreset(roleId: string): void {
		const role = builtinRoles.find((r) => r.id === roleId);
		if (role) permissionsSelector?.applyPreset(role.permissions);
	}
</script>

<div class="flex gap-4">
	<label class="flex items-center gap-2">
		<input
			type="radio"
			name="sa-mode"
			checked={mode === 'custom'}
			onchange={() => selectMode('custom')}
		/>
		{m.customPermissions()}
	</label>
	<label class="flex items-center gap-2">
		<input
			type="radio"
			name="sa-mode"
			checked={mode === 'role'}
			onchange={() => selectMode('role')}
		/>
		{m.useRoleDirectly()}
	</label>
</div>

{#if mode === 'role'}
	<label class="label space-y-1">
		<span class="font-semibold">{m.role()}<span class="text-error-500"> *</span></span>
		<select class="select" value={selectedRoleId} onchange={(e) => pickRole(e.currentTarget.value)}>
			<option value="">{m.select()}</option>
			{#each builtinRoles as role (role.id)}
				<option value={role.id}>{role.name}</option>
			{/each}
		</select>
		<p class="text-sm opacity-75 font-normal">{m.useRoleDirectlyHelpText()}</p>
	</label>
{:else}
	<label class="label space-y-1">
		<span class="font-semibold">{m.startFromRole()}</span>
		<select class="select" onchange={(e) => applyRolePreset(e.currentTarget.value)}>
			<option value="">{m.select()}</option>
			{#each builtinRoles as role (role.id)}
				<option value={role.id}>{role.name}</option>
			{/each}
		</select>
		<p class="text-sm opacity-75 font-normal">{m.startFromRoleHelpText()}</p>
	</label>
	<ListSelector
		{form}
		field="permissions"
		label={m.permissions()}
		optionsEndpoint="service-accounts/permissions"
		optionsLabelField="normalized_codename"
		groupBy={[{ field: 'content_type', path: ['app_label'] }, { field: 'normalized_model' }]}
		cacheLock={cacheLocks['permissions']}
		bind:cachedValue={formDataCache['permissions']}
		bind:this={permissionsSelector}
	/>
{/if}
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="folders"
	field="perimeter_folders"
	cacheLock={cacheLocks['perimeter_folders']}
	bind:cachedValue={formDataCache['perimeter_folders']}
	label={m.domains()}
/>
<Checkbox
	{form}
	field="is_recursive"
	label={m.isRecursive()}
	helpText={m.isRecursiveHelpText()}
	cacheLock={cacheLocks['is_recursive']}
	bind:cachedValue={formDataCache['is_recursive']}
/>
<TextField
	type="date"
	{form}
	field="expiry_date"
	label={m.expiryDate()}
	helpText={m.serviceAccountExpiryHelpText()}
	cacheLock={cacheLocks['expiry_date']}
	bind:cachedValue={formDataCache['expiry_date']}
/>
