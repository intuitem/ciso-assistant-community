<script lang="ts">
	import { complianceColorMap } from './utils';
	import { page } from '$app/stores';

	export let name: string;
	export let description: string;
	export let ra_id: string | undefined = undefined;
	export let leaf_content: string;
	export let threats: Record<string, any>[] | undefined = undefined;
	export let security_functions: Record<string, any>[] | undefined = undefined;
	export let children: Record<string, Record<string, unknown>> | undefined = undefined;
	export let canEditRequirementAssessment: boolean;
	export let status: string | undefined = undefined;
	export let statusCounts: Record<string, number> | undefined;

	$: hasChildren = children && Object.keys(children).length > 0;

	const content: string = leaf_content
		? leaf_content
		: description
		? `${name} ${description}`
		: name;

	let showInfo = false;

	const getLeaves = (children: Record<string, any>[] | undefined, leaves: any = []) => {
		if (children?.length === 0) return leaves;
		for (const value of Object.values(children)) {
			if (value.children && Object.keys(value.children).length > 0) {
				getLeaves(value.children, leaves);
			} else {
				leaves.push(value);
			}
		}
		return leaves;
	};

	const leaves = getLeaves(children) ?? [];

	const REQUIREMENT_ASSESSMENT_STATUS = [
		'compliant',
		'partially_compliant',
		'in_progress',
		'non_compliant',
		'not_applicable',
		'to_do'
	] as const;

	type StatusPercentage = {
		status: (typeof REQUIREMENT_ASSESSMENT_STATUS)[number];
		percentage: {
			value: number;
			display: string;
		};
	};

	const orderedStatusPercentages: StatusPercentage[] = REQUIREMENT_ASSESSMENT_STATUS.map(
		(status) => {
			if (!statusCounts) return { status, percentage: { value: 0, display: '0' } };
			const value = statusCounts[status] || 0;
			const percentValue: number = (value / leaves.length) * 100;
			const percentage = {
				value: percentValue,
				display: percentValue.toFixed(0)
			};
			return { status, percentage };
		}
	);

	$: classesShowInfo = (show: boolean) => (!show ? 'hidden' : '');
	$: classesShowInfoText = (show: boolean) => (show ? 'text-primary-500' : '');
</script>

<div class="flex flex-row justify-between">
	<div class="flex flex-col w-1/2">
		<span style="font-weight: {hasChildren ? 600 : 300};">
			{#if !hasChildren && canEditRequirementAssessment}
				<span class="w-full h-full flex p-4 rounded-token hover:text-primary-500">
					<a href="/requirement-assessments/{ra_id}?next={$page.url.pathname}">
						{content}
					</a>
				</span>
			{:else}
				{content}
			{/if}
		</span>
		{#if threats || security_functions}
			<div
				role="button"
				tabindex="-1"
				class="underline text-sm hover:text-primary-400 {classesShowInfoText(showInfo)}"
				on:click={(_) => (showInfo = !showInfo)}
				on:keydown={(_) => (showInfo = !showInfo)}
			>
				<i class="text-xs fa-solid fa-info-circle" /> Learn more
			</div>
			<div
				class="card p-2 variant-ghost-primary text-sm flex flex-row cursor-auto {classesShowInfo(
					showInfo
				)}"
			>
				<div class="flex-1">
					<p class="font-medium">
						<i class="fa-solid fa-gears" />
						Suggested security functions
					</p>
					{#if security_functions?.length === 0}
						<p>--</p>
					{:else if security_functions}
						<ul class="list-disc ml-4">
							{#each security_functions as func}
								<li>
									{#if func.id}
										<a
											class="anchor"
											href="/security-functions/{func.id}?next={$page.url.pathname}"
										>
											{func.name}
										</a>
									{:else}
										<p>{func.name}</p>
									{/if}
								</li>
							{/each}
						</ul>
					{/if}
				</div>
				<div class="flex-1">
					<p class="font-medium">
						<i class="fa-solid fa-gears" />
						Threats covered
					</p>
					{#if threats?.length === 0}
						<p>--</p>
					{:else if threats}
						<ul class="list-disc ml-4">
							{#each threats as threat}
								<li>
									{#if threat.id}
										<a class="anchor" href="/threats/{threat.id}?next={$page.url.pathname}">
											{threat.name}
										</a>
									{:else}
										<p>{threat.name}</p>
									{/if}
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			</div>
		{/if}
	</div>
	{#if hasChildren}
		<div class="flex flex-1 bg-gray-200 rounded-full overflow-hidden h-4 shrink">
			{#each orderedStatusPercentages as sp}
				{#if complianceColorMap[sp.status] === '#000000'}
					<div
						class="flex flex-col justify-center overflow-hidden text-white text-xs text-center bg-yellow-500"
						style="width: {sp.percentage.value}%; background-color: {complianceColorMap[sp.status]}"
					>
						{sp.percentage.display}%
					</div>
				{:else}
					<div
						class="flex flex-col justify-center overflow-hidden text-black text-xs text-center bg-yellow-500"
						style="width: {sp.percentage.value}%; background-color: {complianceColorMap[sp.status]}"
					>
						{sp.percentage.display}%
						<!-- {sp.percentage?.display}% -->
					</div>
				{/if}
			{/each}
		</div>
	{/if}
</div>
