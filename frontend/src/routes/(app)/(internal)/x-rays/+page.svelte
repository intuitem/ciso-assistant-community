<script lang="ts">
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const aggregateQualityChecks = (item: any) => {
		const types = ['errors', 'warnings', 'info'];
		const result = {};

		types.forEach((type) => {
			result[type] = Object.entries(item.objects).reduce((acc, [key, value]) => {
				if (key !== 'object') {
					// if key === 'quality_check'
					acc = [...acc, ...value.quality_check[type]];
				}
				return acc;
			}, []);
		});

		return result;
	};

	let tabStates = $state({});

	const processPerimetersData = (rawData: any) => {
		return Object.entries(rawData).map(([key, value]) => {
			return {
				id: key,
				...(value as Record<string, any>),
				compliance_assessments: {
					...value.compliance_assessments,
					...aggregateQualityChecks(value.compliance_assessments)
				},
				risk_assessments: {
					...value.risk_assessments,
					...aggregateQualityChecks(value.risk_assessments)
				}
			};
		});
	};
</script>

<div class="card bg-white p-6 shadow-sm flex flex-col space-y-4">
	{#await data.stream.data}
		<div class="flex flex-col items-center justify-center py-8">
			<div class="text-sm text-gray-600 mb-4">Loading data...</div>
			<LoadingSpinner />
		</div>
	{:then rawData}
		{@const perimeters = processPerimetersData(rawData)}
		{#if perimeters.length == 0}
			<span class="text-2xl">{m.xRaysEmptyMessage()}</span>
		{/if}
		{#each perimeters as perimeter, index}
		{@const compliance_assessments = Object.values(perimeter.compliance_assessments.objects)}
		{@const risk_assessments = Object.values(perimeter.risk_assessments.objects)}
		<div>
			<span class="text-2xl">💡</span>
			<Anchor
				class="text-2xl font-bold mb-1 hover:underline text-blue-600"
				href="/perimeters/{perimeter.perimeter.id}"
			>
				{perimeter.perimeter.folder.str}/{perimeter.perimeter.name}
			</Anchor>
			<Tabs
				value={tabStates[perimeter.id] || 'compliance_assessments'}
				onValueChange={(e) => {
					if (!tabStates[perimeter.id]) {
						tabStates[perimeter.id] = 'compliance_assessments';
					}
					tabStates[perimeter.id] = e.value;
				}}
				listJustify="justify-center"
			>
				{#snippet list()}
					<Tabs.Control value="compliance_assessments" labelBase="inert px-2"
						>{m.complianceAssessments()}
						{#if perimeter.compliance_assessments.errors.length > 0}
							<span class="badge preset-tonal-error"
								>{perimeter.compliance_assessments.errors.length}</span
							>
						{/if}
						{#if perimeter.compliance_assessments.warnings.length > 0}
							<span class="badge preset-tonal-warning"
								>{perimeter.compliance_assessments.warnings.length}</span
							>
						{/if}
						{#if perimeter.compliance_assessments.info.length > 0}
							<span class="badge preset-tonal-secondary"
								>{perimeter.compliance_assessments.info.length}</span
							>
						{/if}
					</Tabs.Control>
					<Tabs.Control value="risk_assessments" labelBase="inert px-2"
						>{m.riskAssessments()}
						{#if perimeter.risk_assessments.errors.length > 0}
							<span class="badge preset-tonal-error"
								>{perimeter.risk_assessments.errors.length}</span
							>
						{/if}
						{#if perimeter.risk_assessments.warnings.length > 0}
							<span class="badge preset-tonal-warning"
								>{perimeter.risk_assessments.warnings.length}</span
							>
						{/if}
						{#if perimeter.risk_assessments.info.length > 0}
							<span class="badge preset-tonal-secondary"
								>{perimeter.risk_assessments.info.length}</span
							>
						{/if}
					</Tabs.Control>
				{/snippet}
				{#snippet content()}
					<Tabs.Panel value="compliance_assessments">
						<ul class="list-none pl-4 text-sm space-y-2">
							{#each compliance_assessments as compliance_assessment, index}
								<li class="h4 font-semibold mb-1">
									<Anchor
										href="/compliance-assessments/{compliance_assessment.object.id}"
										class="hover:underline text-blue-600"
										>{compliance_assessment.object.name}</Anchor
									>
								</li>
								{@const quality_check = compliance_assessment.quality_check}
								<div class="flex flex-col space-y-3">
									{#if quality_check.errors.length > 0}
										<div class="space-y-2">
											<div class="preset-tonal-error rounded-base px-2 py-1">
												<i class="fa-solid fa-bug mr-1"></i>
												{#if quality_check.errors.length === 1}
													<span class="font-bold">{quality_check.errors.length}</span>
													{m.errorsFound({ s: '' })}
												{:else}
													<span class="font-bold">{quality_check.errors.length}</span>
													{m.errorsFound({ s: '' })}
												{/if}
											</div>
											<ul class="list-disc pl-4 text-sm">
												{#each quality_check.errors as error}
													<li>
														{#if error.object.name}<Anchor class="anchor" href={error.link}
																>{error.object.name}</Anchor
															>:{/if}
														{safeTranslate(error.msgid)}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
									{#if quality_check.warnings.length > 0}
										<div class="space-y-2">
											<div class="preset-tonal-warning rounded-base px-2 py-1">
												<i class="fa-solid fa-triangle-exclamation mr-1"></i>
												{#if quality_check.warnings.length === 1}
													<span class="font-bold">{quality_check.warnings.length}</span>
													{m.warningsFound({ s: '' })}
												{:else}
													<span class="font-bold">{quality_check.warnings.length}</span>
													{m.warningsFound({ s: 's' })}
												{/if}
											</div>
											<ul class="list-disc pl-4 text-sm">
												{#each quality_check.warnings as warning}
													<li>
														{#if warning.object.name}
															<Anchor class="anchor" href={warning.link}
																>{warning.object.name}</Anchor
															>:
														{/if}
														{safeTranslate(warning.msgid)}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
									{#if quality_check.info.length > 0}
										<div class="space-y-2">
											<div class="preset-tonal-secondary rounded-base px-2 py-1">
												<i class="fa-solid fa-circle-info mr-1"></i>
												{#if quality_check.info.length === 1}
													<span class="font-bold">{quality_check.info.length}</span>
													{m.infosFound({ s: '' })}
												{:else}
													<span class="font-bold">{quality_check.info.length}</span>
													{m.infosFound({ s: 's' })}
												{/if}
											</div>
											<ul class="list-disc pl-4 text-sm">
												{#each quality_check.info as info}
													<li>
														{#if info.object.name}<Anchor class="anchor" href={info.link}
																>{info.object.name}</Anchor
															>:{/if}
														{safeTranslate(info.msgid)}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
								</div>
								{#if index != compliance_assessments.length - 1}
									<hr />
								{/if}
							{/each}
						</ul>
					</Tabs.Panel>
					<Tabs.Panel value="risk_assessments">
						<ul class="list-none pl-4 text-sm space-y-2">
							{#each risk_assessments as risk_assessment, index}
								<li class="h4 font-semibold mb-1">
									<Anchor
										href="/risk-assessments/{risk_assessment.object.id}"
										class="hover:underline text-blue-600">{risk_assessment.object.name}</Anchor
									>
								</li>
								{@const quality_check = risk_assessment.quality_check}
								<div class="flex flex-col space-y-3">
									{#if quality_check.errors.length > 0}
										<div class="space-y-2">
											<div class="preset-tonal-error rounded-base px-2 py-1">
												<i class="fa-solid fa-bug mr-1"></i>
												{#if quality_check.errors.length === 1}
													<span class="font-bold">{quality_check.errors.length}</span>
													{m.errorsFound({ s: '' })}
												{:else}
													<span class="font-bold">{quality_check.errors.length}</span>
													{m.errorsFound({ s: '' })}
												{/if}
											</div>
											<ul class="list-disc pl-4 text-sm">
												{#each quality_check.errors as error}
													<li>
														{#if error.object.name}<Anchor class="anchor" href={error.link}
																>{error.object.name}</Anchor
															>:{/if}
														{safeTranslate(error.msgid)}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
									{#if quality_check.warnings.length > 0}
										<div class="space-y-2">
											<div class="preset-tonal-warning rounded-base px-2 py-1">
												<i class="fa-solid fa-triangle-exclamation mr-1"></i>
												{#if quality_check.warnings.length === 1}
													<span class="font-bold">{quality_check.warnings.length}</span>
													{m.warningsFound({ s: '' })}
												{:else}
													<span class="font-bold">{quality_check.warnings.length}</span>
													{m.warningsFound({ s: 's' })}
												{/if}
											</div>
											<ul class="list-disc pl-4 text-sm">
												{#each quality_check.warnings as warning}
													<li>
														{#if warning.object.name}<Anchor class="anchor" href={warning.link}
																>{warning.object.name}</Anchor
															>:{/if}
														{safeTranslate(warning.msgid)}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
									{#if quality_check.info.length > 0}
										<div class="space-y-2">
											<div class="preset-tonal-secondary rounded-base px-2 py-1">
												<i class="fa-solid fa-circle-info mr-1"></i>
												{#if quality_check.info.length === 1}
													<span class="font-bold">{quality_check.info.length}</span>
													{m.infosFound({ s: '' })}
												{:else}
													<span class="font-bold">{quality_check.info.length}</span>
													{m.infosFound({ s: 's' })}
												{/if}
											</div>
											<ul class="list-disc pl-4 text-sm">
												{#each quality_check.info as info}
													<li>
														{#if info.object.name}<Anchor class="anchor" href={info.link}
																>{info.object.name}</Anchor
															>:{/if}
														{safeTranslate(info.msgid)}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
								</div>
								{#if index != risk_assessments.length - 1}
									<hr />
								{/if}
							{/each}
						</ul>
					</Tabs.Panel>
				{/snippet}
			</Tabs>
		</div>
		{#if index != perimeters.length - 1}
			<hr />
		{/if}
	{/each}
	{:catch error}
		<div class="flex flex-col items-center justify-center py-8">
			<p class="text-red-500">Error loading data</p>
		</div>
	{/await}
</div>
