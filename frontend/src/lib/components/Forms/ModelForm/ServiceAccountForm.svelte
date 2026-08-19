<script lang="ts">
	import { onMount } from 'svelte';
	import { formFieldProxy } from 'sveltekit-superforms';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Checkbox from '../Checkbox.svelte';
	import ListSelector from '../ListSelector.svelte';
	import RadioGroup from '$lib/components/Forms/RadioGroup.svelte';
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
		global_only?: boolean;
		permissions: number[];
	}

	type AuthorizationMode = 'custom' | 'role' | 'global_admin';

	const IDENTITY_SOURCE_OPTIONS = [
		{ id: 'local', label: m.local() },
		{ id: 'federated', label: m.federated() }
	];

	let builtinRoles: BuiltinRole[] = $state([]);
	let rootFolderId: string = $state('');
	let permissionsSelector: ReturnType<typeof ListSelector> | undefined = $state();

	const { value: roleValue } = formFieldProxy(form, 'role');
	const { value: permissionsValue } = formFieldProxy(form, 'permissions');
	const { value: perimeterValue } = formFieldProxy(form, 'folders');
	const { value: isRecursiveValue } = formFieldProxy(form, 'is_recursive');
	const { value: identitySource } = formFieldProxy(form, 'identity_source');

	const initialMode: AuthorizationMode =
		context === 'edit' &&
		(object.authorization_mode === 'global_admin' || object.authorization_mode === 'role')
			? object.authorization_mode
			: 'custom';
	let mode: AuthorizationMode = $state(initialMode);
	let customPermissions: number[] = $state(
		initialMode === 'custom' && Array.isArray(object.permissions) ? object.permissions : []
	);
	let selectedRoleId: string = $state(
		initialMode === 'role' && typeof object.role === 'string' ? object.role : ''
	);
	// Scope stashed when entering global-admin mode, restored on the way back.
	let savedScope: { folders: string[]; is_recursive: boolean } | null = $state(null);

	// The Administrator role is only linkable through the explicit global-admin
	// mode, which forces the perimeter to the Global folder, recursive.
	let globalAdminRole = $derived(builtinRoles.find((role) => role.global_only));
	let selectableRoles = $derived(builtinRoles.filter((role) => !role.global_only));

	setAuthorizationFields(mode);

	onMount(async () => {
		const [rolesRes, foldersRes] = await Promise.all([
			fetch('/service-accounts/roles'),
			fetch('/folders?content_type=GL')
		]);
		if (rolesRes.ok) builtinRoles = await rolesRes.json();
		if (foldersRes.ok) rootFolderId = (await foldersRes.json()).results?.[0]?.id ?? '';
		// The forced global-admin fields depend on these fetches: apply them
		// now if the mode was set before the data was available. Event-driven
		// on purpose — a reactive $effect writing the form store loops against
		// superforms' own store updates (effect_update_depth_exceeded).
		if (mode === 'global_admin') {
			setAuthorizationFields('global_admin');
		}
	});

	function setAuthorizationFields(next: AuthorizationMode): void {
		form.form.update((data) => {
			const updated = { ...data };
			updated.authorization_mode = next;
			if (next === 'custom') {
				delete updated.role;
				updated.permissions = customPermissions;
			} else if (next === 'role') {
				delete updated.permissions;
				if (selectedRoleId) updated.role = selectedRoleId;
				else delete updated.role;
			} else {
				delete updated.permissions;
				if (globalAdminRole) updated.role = globalAdminRole.id;
				if (rootFolderId) updated.folders = [rootFolderId];
				updated.is_recursive = true;
			}
			return updated;
		});
	}

	function selectMode(next: AuthorizationMode): void {
		if (next === mode) return;

		if (mode === 'custom') {
			customPermissions = Array.isArray($permissionsValue)
				? $permissionsValue.filter(
						(permission): permission is number => typeof permission === 'number'
					)
				: [];
		}
		if (next === 'global_admin') {
			savedScope = {
				folders: Array.isArray($perimeterValue) ? [...$perimeterValue] : [],
				is_recursive: Boolean($isRecursiveValue ?? true)
			};
		}

		mode = next;
		formDataCache['permissions'] = customPermissions;
		setAuthorizationFields(next);

		if (next !== 'global_admin' && savedScope) {
			const scope = savedScope;
			savedScope = null;
			form.form.update((data) => ({
				...data,
				folders: scope.folders,
				is_recursive: scope.is_recursive
			}));
		}
	}

	function pickRole(roleId: string): void {
		selectedRoleId = roleId;
		$roleValue = roleId || undefined;
	}

	function applyRolePreset(roleId: string): void {
		const role = builtinRoles.find((r) => r.id === roleId);
		if (role) permissionsSelector?.applyPreset(role.permissions);
	}

	function handleIdentitySourceChange(value: string): void {
		if (value !== 'local') return;
		form.form.update((data) => {
			const updated = { ...data };
			delete updated.social_app;
			delete updated.federated_subject;
			return updated;
		});
		formDataCache['social_app'] = undefined;
		formDataCache['federated_subject'] = undefined;
	}
</script>

{#if context !== 'edit'}
	<RadioGroup
		{form}
		field="identity_source"
		label={m.identitySource()}
		helpText={m.identitySourceHelpText()}
		possibleOptions={IDENTITY_SOURCE_OPTIONS}
		key="id"
		labelKey="label"
		onChange={handleIdentitySourceChange}
		cacheLock={cacheLocks['identity_source']}
		bind:cachedValue={formDataCache['identity_source']}
	/>
{/if}
{#if $identitySource === 'federated'}
	<AutocompleteSelect
		{form}
		mandatory
		optionsEndpoint="service-accounts/social-apps"
		optionsLabelField="name"
		field="social_app"
		label={m.socialApp()}
		helpText={m.socialAppHelpText()}
		cacheLock={cacheLocks['social_app']}
		bind:cachedValue={formDataCache['social_app']}
	/>
	<TextField
		{form}
		field="federated_subject"
		label={m.federatedSubject()}
		helpText={m.federatedSubjectHelpText()}
		cacheLock={cacheLocks['federated_subject']}
		bind:cachedValue={formDataCache['federated_subject']}
	/>
{/if}
<div class="flex flex-wrap gap-4">
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
	<label class="flex items-center gap-2">
		<input
			type="radio"
			name="sa-mode"
			checked={mode === 'global_admin'}
			onchange={() => selectMode('global_admin')}
		/>
		{m.globalAdmin()}
	</label>
</div>

{#if mode === 'global_admin'}
	<div class="card p-4 preset-tonal-warning text-sm" data-testid="global-admin-notice">
		<i class="fa-solid fa-triangle-exclamation mr-2"></i>{m.serviceAccountGlobalAdminHelpText()}
	</div>
{:else if mode === 'role'}
	<label class="label space-y-1">
		<span class="font-semibold">{m.role()}<span class="text-error-500"> *</span></span>
		<select class="select" value={selectedRoleId} onchange={(e) => pickRole(e.currentTarget.value)}>
			<option value="">{m.select()}</option>
			{#each selectableRoles as role (role.id)}
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
			{#each selectableRoles as role (role.id)}
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
{#if mode !== 'global_admin'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="folders"
		field="folders"
		cacheLock={cacheLocks['folders']}
		bind:cachedValue={formDataCache['folders']}
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
{/if}
<TextField
	type="date"
	{form}
	field="expiry_date"
	label={m.expiryDate()}
	helpText={m.serviceAccountExpiryHelpText()}
	cacheLock={cacheLocks['expiry_date']}
	bind:cachedValue={formDataCache['expiry_date']}
/>
