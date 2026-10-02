<script lang="ts">
	import { onMount } from 'svelte';
	import * as m from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';

	const IAM_GROUP_USER_GROUP_NAMES = [
		"BI-UG-AUD",
    "BI-UG-APP",
    "BI-UG-ANA",
    "BI-UG-DMA",
    "BI-UG-ADE",
    "BI-UG-TST",
	] as const;
	type UserGroupName = (typeof IAM_GROUP_USER_GROUP_NAMES)[number];

	interface IAMGroupConfig {
		active: boolean
		is_recursive: boolean
	}
	interface IAMGroup {
		user_group_name: UserGroupName
		is_recursive: boolean
	}

	interface Role {
		name: string
		codename: string
		builtin: boolean
		[key: string]: unknown
	};

	function getUserGroupNameFromRoleName(roleCodename: Role["codename"]): UserGroupName {
		const userGroupName = roleCodename.replaceAll("-RL-", "-UG-");
		return userGroupName as UserGroupName;
	}

	interface Props {
		form?: SuperValidated<any> | { form: null };
		value?: IAMGroup[]
		classes?: string
	}

	let {
		form = { form: null },
		value = $bindable([]),
		classes = "",
	}: Props = $props();

	const { form: formData } = form;

	let iamGroupConfigs = $state(
		Object.fromEntries(IAM_GROUP_USER_GROUP_NAMES.map(
				(userGroupName) => [userGroupName, { active: false, is_recursive: false }]
			)
		) as Record<UserGroupName, IAMGroupConfig>
	);

	// Translated (by the backend) name of the role behind each IAM user group.
	let translatedRoleNameMap: Partial<Record<UserGroupName, string>> = $state({});

	onMount(() => {
    const iamGroups = (formData !== null ? $formData.iam_groups : value) ?? [];

    for (const {user_group_name, is_recursive} of iamGroups) {
      iamGroupConfigs[user_group_name as UserGroupName] = {
        active: true,
        is_recursive: is_recursive,
      }
    }
    if (formData !== null) {
      updateFormIAMGroups();
    }

		fetch('/roles?limit=100').then((res) => res.json()).then((responseData: { results?: Role[] }) => {
			const roles: Role[] = responseData?.results ?? [];

			for (const role of roles) {
				const userGroupName = getUserGroupNameFromRoleName(role.codename);

				if (role.builtin && IAM_GROUP_USER_GROUP_NAMES.includes(userGroupName)) {
					translatedRoleNameMap[userGroupName as UserGroupName] = role.name;
				}
			}
		});
	});

	function updateFormIAMGroups() {
		const newIAMGroups: IAMGroup[] = [];

		for (const [user_group_name, {active, is_recursive}] of Object.entries(iamGroupConfigs)) {
			if (active) {
				const iamGroup: IAMGroup = {user_group_name, is_recursive};
				newIAMGroups.push(iamGroup);
			}
		}

		value = newIAMGroups;
	}

	$effect(() => {
		if (formData !== null) {
			formData.update((_formData) => {
				_formData.iam_groups = value;
				return _formData;
			});
		}
	});
</script>

<!-- One grid for all the rows so the name / "create" / "recursive" columns line up. -->
<div class="grid grid-cols-[repeat(3,max-content)] justify-start items-center gap-x-6 gap-y-3 {classes}">
	{#each IAM_GROUP_USER_GROUP_NAMES as iamGroupName, index}
		{#if translatedRoleNameMap[iamGroupName] !== undefined}
			<h2>{translatedRoleNameMap[iamGroupName]}:</h2>
			<div class="flex items-center gap-2">
				<label class="label font-medium" for={`iam-group-active-${index}`}>{m.addRole()}:</label>
				<input
					name=""
					type="checkbox"
					class="checkbox"
					id={`iam-group-active-${index}`}
					bind:checked={iamGroupConfigs[iamGroupName].active}
					onchange={() => updateFormIAMGroups()}
				/>
			</div>
			<div class="flex items-center gap-2">
				<label class="label font-medium" for={`iam-group-is-recursive-${index}`}>{m.isRecursive()}:</label>
				<input
					name=""
					type="checkbox"
					class="checkbox"
					id={`iam-group-is-recursive-${index}`}
					bind:checked={iamGroupConfigs[iamGroupName].is_recursive}
					onchange={() => updateFormIAMGroups()}
				/>
			</div>
		{/if}
	{/each}
</div>
