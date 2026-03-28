<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { invalidateAll } from '$app/navigation';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { onMount } from 'svelte';

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	const cBase = 'card bg-white p-6 w-modal-wide space-y-6';
	const cHeader = 'text-xl font-medium text-gray-900';

	interface Props {
		parent: any;
		processingId: string;
		urlModel: string;
	}

	let { parent, processingId, urlModel }: Props = $props();

	// Groups defined by category key prefixes/ranges, labels fetched from backend
	const groupDefinitions: { label: string; keys: string[] }[] = [
		{
			label: 'Basic Identity Information',
			keys: [
				'privacy_basic_identity',
				'privacy_name',
				'privacy_identification_numbers',
				'privacy_online_identifiers',
				'privacy_location_data'
			]
		},
		{
			label: 'Contact Information',
			keys: ['privacy_contact_details', 'privacy_address', 'privacy_email', 'privacy_phone_number']
		},
		{
			label: 'Financial Information',
			keys: [
				'privacy_financial_data',
				'privacy_bank_account',
				'privacy_payment_card',
				'privacy_transaction_history',
				'privacy_salary_information'
			]
		},
		{
			label: 'Sensitive Personal Data',
			keys: [
				'privacy_health_data',
				'privacy_genetic_data',
				'privacy_biometric_data',
				'privacy_racial_ethnic_origin',
				'privacy_political_opinions',
				'privacy_religious_beliefs',
				'privacy_trade_union_membership',
				'privacy_sexual_orientation',
				'privacy_sex_life_data'
			]
		},
		{
			label: 'Digital Behavior and Activities',
			keys: [
				'privacy_browsing_history',
				'privacy_search_history',
				'privacy_cookies',
				'privacy_device_information',
				'privacy_ip_address',
				'privacy_user_behavior'
			]
		},
		{
			label: 'Professional Data',
			keys: [
				'privacy_employment_details',
				'privacy_education_history',
				'privacy_professional_qualifications',
				'privacy_work_performance'
			]
		},
		{
			label: 'Social Relationships',
			keys: ['privacy_family_details', 'privacy_social_network', 'privacy_lifestyle_information']
		},
		{
			label: 'Communication Data',
			keys: [
				'privacy_correspondence',
				'privacy_messaging_content',
				'privacy_communication_metadata'
			]
		},
		{
			label: 'Government / Official Data',
			keys: [
				'privacy_government_identifiers',
				'privacy_tax_information',
				'privacy_social_security',
				'privacy_drivers_license',
				'privacy_passport_information'
			]
		},
		{
			label: 'Legal Data',
			keys: ['privacy_legal_records', 'privacy_criminal_records', 'privacy_judicial_data']
		},
		{
			label: 'Preferences and Opinions',
			keys: ['privacy_preferences', 'privacy_opinions', 'privacy_feedback']
		},
		{
			label: 'Other Types',
			keys: [
				'privacy_images_photos',
				'privacy_voice_recordings',
				'privacy_video_recordings',
				'privacy_other'
			]
		}
	];

	let categoryLabels: Record<string, string> = $state({});
	let selectedCategories: string[] = $state([]);
	let retention = $state('');
	let deletionPolicy = $state('');
	let isSensitive = $state(false);
	let submitting = $state(false);
	let loading = $state(true);
	let deletionPolicyOptions: { value: string; label: string }[] = $state([]);

	const categoryGroups = $derived(
		groupDefinitions.map((g) => ({
			label: g.label,
			categories: g.keys
				.filter((k) => k in categoryLabels)
				.map((k) => ({ value: k, label: categoryLabels[k] }))
		}))
	);

	const canSubmit = $derived(selectedCategories.length > 0 && !submitting);

	function parseChoices(data: any): Record<string, string> {
		if (Array.isArray(data)) {
			const result: Record<string, string> = {};
			for (const item of data) {
				result[item.value] = item.label;
			}
			return result;
		}
		return data;
	}

	onMount(async () => {
		try {
			const [catRes, delRes] = await Promise.all([
				fetch(`/${urlModel}/batch-create?options=category`),
				fetch(`/${urlModel}/batch-create?options=deletion_policy`)
			]);
			if (catRes.ok) {
				categoryLabels = parseChoices(await catRes.json());
			}
			if (delRes.ok) {
				const choices = parseChoices(await delRes.json());
				deletionPolicyOptions = Object.entries(choices).map(([key, val]) => ({
					value: key,
					label: val
				}));
			}
		} catch (e) {
			console.error('Failed to fetch options', e);
		} finally {
			loading = false;
		}
	});

	function toggleCategory(value: string) {
		if (selectedCategories.includes(value)) {
			selectedCategories = selectedCategories.filter((v) => v !== value);
		} else {
			selectedCategories = [...selectedCategories, value];
		}
	}

	function toggleGroup(group: (typeof categoryGroups)[0]) {
		const groupValues = group.categories.map((c) => c.value);
		const allSelected = groupValues.every((v) => selectedCategories.includes(v));
		if (allSelected) {
			selectedCategories = selectedCategories.filter((v) => !groupValues.includes(v));
		} else {
			const toAdd = groupValues.filter((v) => !selectedCategories.includes(v));
			selectedCategories = [...selectedCategories, ...toAdd];
		}
	}

	function selectAll() {
		selectedCategories = categoryGroups.flatMap((g) => g.categories.map((c) => c.value));
	}

	function deselectAll() {
		selectedCategories = [];
	}

	async function handleSubmit() {
		submitting = true;
		try {
			const res = await fetch(`/${urlModel}/batch-create`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					processing: processingId,
					categories: selectedCategories,
					retention,
					deletion_policy: deletionPolicy,
					is_sensitive: isSensitive
				})
			});

			const data = await res.json();

			if (res.ok && data.success) {
				const messages = [];
				if (data.created > 0) {
					messages.push(m.batchCreatePersonalDataCreated({ count: data.created }));
				}
				if (data.skipped > 0) {
					messages.push(m.batchCreatePersonalDataSkipped({ count: data.skipped }));
				}
				if (data.errors?.length > 0) {
					messages.push(`${data.errors.length} error(s)`);
				}
				toastStore.trigger({ message: messages.join(', ') });
				await invalidateAll();
				parent.onClose();
			} else {
				toastStore.trigger({
					message: data.error || 'An error occurred',
					background: 'preset-filled-error-500'
				});
			}
		} catch (e) {
			console.error('Batch create failed', e);
			toastStore.trigger({
				message: 'An error occurred',
				background: 'preset-filled-error-500'
			});
		} finally {
			submitting = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div
		class="modal-example-form {cBase}"
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
	>
		<header id="modal-title" class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>

		{#if loading}
			<div class="flex items-center justify-center py-8">
				<i class="fa-solid fa-spinner fa-spin text-2xl text-gray-400"></i>
			</div>
		{:else}
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- Left: Category selection -->
				<div class="space-y-3">
					<div class="flex items-center justify-between">
						<span class="text-sm font-medium text-gray-700">
							{m.selectCategories()} ({selectedCategories.length})
						</span>
						<div class="flex gap-2">
							<button
								type="button"
								class="text-xs text-indigo-600 hover:text-indigo-800"
								onclick={selectAll}
							>
								{m.selectAll()}
							</button>
							<button
								type="button"
								class="text-xs text-gray-500 hover:text-gray-700"
								onclick={deselectAll}
							>
								{m.deselectAll()}
							</button>
						</div>
					</div>

					<div class="max-h-96 overflow-y-auto border border-gray-200 rounded-lg">
						{#each categoryGroups as group}
							{@const groupValues = group.categories.map((c) => c.value)}
							{@const allGroupSelected = groupValues.every((v) => selectedCategories.includes(v))}
							{@const someGroupSelected =
								!allGroupSelected && groupValues.some((v) => selectedCategories.includes(v))}

							<div class="border-b border-gray-100 last:border-b-0">
								<!-- Group header -->
								<label
									class="flex items-center gap-2 px-3 py-2 bg-gray-50 cursor-pointer font-medium text-sm"
								>
									<input
										type="checkbox"
										checked={allGroupSelected}
										indeterminate={someGroupSelected}
										onchange={() => toggleGroup(group)}
										class="checkbox"
									/>
									<span>{group.label}</span>
								</label>
								<!-- Category items -->
								{#each group.categories as category}
									<label
										class="flex items-center gap-2 px-6 py-1.5 hover:bg-gray-50 cursor-pointer"
									>
										<input
											type="checkbox"
											checked={selectedCategories.includes(category.value)}
											onchange={() => toggleCategory(category.value)}
											class="checkbox"
										/>
										<span class="text-sm">{category.label}</span>
									</label>
								{/each}
							</div>
						{/each}
					</div>
				</div>

				<!-- Right: Common fields -->
				<div class="space-y-4">
					<div>
						<label for="retention" class="block text-sm font-medium text-gray-700 mb-1">
							{m.retention()}
						</label>
						<input
							id="retention"
							type="text"
							bind:value={retention}
							class="input w-full border border-gray-300 rounded px-3 py-2 text-sm"
							placeholder={m.retentionPlaceholder()}
						/>
					</div>

					<div>
						<label for="deletion-policy" class="block text-sm font-medium text-gray-700 mb-1">
							{m.deletionPolicy()}
						</label>
						<select
							id="deletion-policy"
							bind:value={deletionPolicy}
							class="select w-full border border-gray-300 rounded px-3 py-2"
						>
							<option value="">--</option>
							{#each deletionPolicyOptions as option}
								<option value={option.value}>{option.label}</option>
							{/each}
						</select>
					</div>

					<div>
						<label class="flex items-center gap-2 cursor-pointer">
							<input type="checkbox" bind:checked={isSensitive} class="checkbox" />
							<span class="text-sm font-medium text-gray-700">{m.isSensitive()}</span>
						</label>
					</div>
				</div>
			</div>
		{/if}

		<footer class="flex gap-3 justify-end pt-4 border-t border-gray-200">
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
				onclick={parent.onClose}
			>
				{m.cancel()}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
				disabled={!canSubmit}
				onclick={handleSubmit}
			>
				{#if submitting}
					<i class="fa-solid fa-spinner fa-spin mr-2"></i>
				{/if}
				{m.create()} ({selectedCategories.length})
			</button>
		</footer>
	</div>
{/if}
