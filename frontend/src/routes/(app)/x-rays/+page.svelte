<script lang="ts">
	import { Tab, TabGroup } from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages';
	import { localItems } from '$lib/utils/locales';

	export let data: PageData;

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

	const projects = Object.entries(data.data).map(([key, value]) => {
		return {
			id: key,
			tabSet: 0,
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
</script>

<div class="card bg-white p-6 shadow flex flex-col space-y-4">
	{#each projects as project, index}
		{@const compliance_assessments = Object.values(project.compliance_assessments.objects)}
		{@const risk_assessments = Object.values(project.risk_assessments.objects)}
		<div>
			<span class="text-2xl">&#128161;</span>
			<a
				class="text-2xl font-bold mb-1 hover:underline text-blue-600"
				href="/projects/{project.project.id}"
			>
				{project.project.folder.str}/{project.project.name}
			</a>
			<TabGroup>
				<Tab bind:group={project.tabSet} name="compliance_assessments_tab" value={0}
					>{m.complianceAssessments()}
					{#if project.compliance_assessments.errors.length > 0}
						<span class="badge variant-soft-error"
							>{project.compliance_assessments.errors.length}</span
						>
					{/if}
					{#if project.compliance_assessments.warnings.length > 0}
						<span class="badge variant-soft-warning"
							>{project.compliance_assessments.warnings.length}</span
						>
					{/if}
					{#if project.compliance_assessments.info.length > 0}
						<span class="badge variant-soft-secondary"
							>{project.compliance_assessments.info.length}</span
						>
					{/if}
				</Tab>
				<Tab bind:group={project.tabSet} name="risk_assessments_tab" value={1}
					>{m.riskAssessments()}
					{#if project.risk_assessments.errors.length > 0}
						<span class="badge variant-soft-error">{project.risk_assessments.errors.length}</span>
					{/if}
					{#if project.risk_assessments.warnings.length > 0}
						<span class="badge variant-soft-warning"
							>{project.risk_assessments.warnings.length}</span
						>
					{/if}
					{#if project.risk_assessments.info.length > 0}
						<span class="badge variant-soft-secondary">{project.risk_assessments.info.length}</span>
					{/if}
				</Tab>
				<svelte:fragment slot="panel">
					{#if project.tabSet === 0}
						<ul class="list-none pl-4 text-sm space-y-2">
							{#each compliance_assessments as compliance_assessment, index}
								<li class="h4 font-semibold mb-1">
									<a
										href="/compliance-assessments/{compliance_assessment.object.id}"
										class="hover:underline text-blue-600">{compliance_assessment.object.name}</a
									>
								</li>
								{@const quality_check = compliance_assessment.quality_check}
								<div class="flex flex-col space-y-3">
									{#if quality_check.errors.length > 0}
										<div class="space-y-2">
											<div class="variant-soft-error rounded-token px-2 py-1">
												<i class="fa-solid fa-bug mr-1" />
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
														{#if error.object.name}<a class="anchor" href={error.link}
																>{error.object.name}</a
															>:{/if}
														{m[error.msgid]()}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
									{#if quality_check.warnings.length > 0}
										<div class="space-y-2">
											<div class="variant-soft-warning rounded-token px-2 py-1">
												<i class="fa-solid fa-triangle-exclamation mr-1" />
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
															<a class="anchor" href={warning.link}>{warning.object.name}</a>:
														{/if}
														{m[warning.msgid]()}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
									{#if quality_check.info.length > 0}
										<div class="space-y-2">
											<div class="variant-soft-secondary rounded-token px-2 py-1">
												<i class="fa-solid fa-circle-info mr-1" />
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
														{#if info.object.name}<a class="anchor" href={info.link}
																>{info.object.name}</a
															>:{/if}
														{m[info.msgid]()}
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
					{/if}
					{#if project.tabSet === 1}
						<ul class="list-none pl-4 text-sm space-y-2">
							{#each risk_assessments as risk_assessment, index}
								<li class="h4 font-semibold mb-1">
									<a
										href="/risk-assessments/{risk_assessment.object.id}"
										class="hover:underline text-blue-600">{risk_assessment.object.name}</a
									>
								</li>
								{@const quality_check = risk_assessment.quality_check}
								<div class="flex flex-col space-y-3">
									{#if quality_check.errors.length > 0}
										<div class="space-y-2">
											<div class="variant-soft-error rounded-token px-2 py-1">
												<i class="fa-solid fa-bug mr-1" />
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
														{#if error.object.name}<a class="anchor" href={error.link}
																>{error.object.name}</a
															>:{/if}
														{m[error.msgid]()}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
									{#if quality_check.warnings.length > 0}
										<div class="space-y-2">
											<div class="variant-soft-warning rounded-token px-2 py-1">
												<i class="fa-solid fa-triangle-exclamation mr-1" />
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
														{#if warning.object.name}<a class="anchor" href={warning.link}
																>{warning.object.name}</a
															>:{/if}
														{m[warning.msgid]()}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
									{#if quality_check.info.length > 0}
										<div class="space-y-2">
											<div class="variant-soft-secondary rounded-token px-2 py-1">
												<i class="fa-solid fa-circle-info mr-1" />
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
														{#if info.object.name}<a class="anchor" href={info.link}
																>{info.object.name}</a
															>:{/if}
														{m[info.msgid]()}
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
					{/if}
				</svelte:fragment>
			</TabGroup>
		</div>
		{#if index != projects.length - 1}
			<hr />
		{/if}
	{/each}
</div>
