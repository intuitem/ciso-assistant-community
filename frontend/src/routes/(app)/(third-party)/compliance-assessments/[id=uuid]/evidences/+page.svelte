<script lang="ts">
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime.js';
	import { onMount } from 'svelte';

	let { data } = $props();
	let evidences = $state([]);
	let loading = $state(true);
	let error = $state(null);

	onMount(async () => {
		try {
			const res = await fetch(`${page.url.pathname}`, {
				headers: {
					'Accept': 'application/json'
				}
			});
			if (!res.ok) {
				throw new Error(`Failed to fetch evidences: ${res.status}`);
			}
			evidences = await res.json();
		} catch (err) {
			error = err.message;
		} finally {
			loading = false;
		}
	});

	function handleLinkClick(linkInfo: any, linkType: string, index: number) {
		const links = linkType === 'direct' ? linkInfo.direct_links : linkInfo.indirect_links;
		if (links && links.length > index) {
			const reqAssessmentId = links[index].requirement_assessment_id;
			window.open(`/requirement-assessments/${reqAssessmentId}/`, '_blank');
		}
	}
</script>

<div class="bg-white p-2 shadow-sm rounded-lg space-x-2 flex flex-row justify-center mb-2">
	<p class="font-semibold text-lg">
		{m.perimeter()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/perimeters/{data.compliance_assessment.perimeter.id}/"
			>{data.compliance_assessment.perimeter.str}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		{m.complianceAssessment()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/compliance-assessments/{data.compliance_assessment.id}/"
			>{data.compliance_assessment.name} - {data.compliance_assessment.version}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		{m.framework()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/frameworks/{data.compliance_assessment.framework.id}/"
			>{data.compliance_assessment.framework.str}</a
		>
	</p>
</div>

<div class="flex flex-col space-y-4 bg-white p-4 shadow-sm rounded-lg">
	<div>
		<p class="text-xl font-extrabold">{m.associatedEvidences()}</p>
		<p class="text-sm text-gray-500">
			{m.evidencesHelpText()}
		</p>
	</div>

	{#if loading}
		<div class="flex justify-center p-8">
			<div class="spinner">Loading...</div>
		</div>
	{:else if error}
		<div class="alert alert-error">
			<p>Error: {error}</p>
		</div>
	{:else if evidences.length === 0}
		<div class="text-center p-8 text-gray-500">
			<p>{m.noEvidencesFound()}</p>
		</div>
	{:else}
		<div class="overflow-x-auto">
			<table class="table table-hover w-full">
				<thead>
					<tr>
						<th>{m.name()}</th>
						<th>{m.status()}</th>
						<th>{m.lastUpdate()}</th>
						<th>{m.expiryDate()}</th>
						<th>{m.owner()}</th>
						<th>{m.relationships()}</th>
					</tr>
				</thead>
				<tbody>
					{#each evidences as evidence}
						<tr>
							<td>
								<a href="/evidences/{evidence.id}/" class="text-primary-500 hover:text-primary-700">
									{evidence.name}
								</a>
							</td>
							<td>{evidence.status}</td>
							<td>
								{evidence.last_update ? formatDateOrDateTime(new Date(evidence.last_update), getLocale()) : '-'}
							</td>
							<td>
								{evidence.expiry_date ? formatDateOrDateTime(new Date(evidence.expiry_date), getLocale()) : '-'}
							</td>
							<td>{evidence.owner.map((user) => user.str).join(', ') || '-'}</td>
							<td>
								<div class="flex flex-col gap-1">
									{#if evidence.link_info.direct_links && evidence.link_info.direct_links.length > 0}
										<div class="text-xs">
											<span class="font-semibold text-green-600">{m.direct()}:</span>
											{#each evidence.link_info.direct_links as link, index}
												<button
													onclick={() => handleLinkClick(evidence.link_info, 'direct', index)}
													class="text-primary-500 hover:text-primary-700 underline block text-left"
													title="Click to view requirement assessment"
												>
													{link.requirement_assessment_name}
												</button>
											{/each}
										</div>
									{/if}
									{#if evidence.link_info.indirect_links && evidence.link_info.indirect_links.length > 0}
										<div class="text-xs">
											<span class="font-semibold text-blue-600">{m.indirect()}:</span>
											{#each evidence.link_info.indirect_links as link, index}
												<button
													onclick={() => handleLinkClick(evidence.link_info, 'indirect', index)}
													class="text-primary-500 hover:text-primary-700 underline block text-left"
													title="{m.viaAppliedControl()}: {link.applied_control_name}"
												>
													{link.requirement_assessment_name}
												</button>
											{/each}
										</div>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
