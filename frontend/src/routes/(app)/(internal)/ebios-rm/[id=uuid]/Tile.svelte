<script lang="ts">
	import { run } from 'svelte/legacy';

	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import { safeTranslate } from '$lib/utils/i18n';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';
	import { browser } from '$app/environment';
	import { Popover, Tooltip } from '@skeletonlabs/skeleton-svelte';

	interface Props {
		title?: string;
		meta?: Record<string, any>[];
		accent_color?: string;
		borderColor?: string;
		createRiskAnalysis?: boolean;
		workshop?: number;
		action?: import('svelte').Snippet;
		content?: import('svelte').Snippet;
		addRiskAnalysis?: import('svelte').Snippet;
	}

	let {
		title = 'activity',
		meta = [],
		accent_color = '',
		borderColor = '',
		createRiskAnalysis = false,
		workshop = 0,
		action,
		content,
		addRiskAnalysis
	}: Props = $props();

	let open = $state(Array(meta.length).fill(false));
	let actionsOpen = $state(Array(meta.length).fill(false));
	let steps = $state(meta);

	let workshopStatus = $derived(() =>
		steps.every((step) => step.status === 'done')
			? 'done'
			: steps.some((step) => step.status === 'done')
				? 'in_progress'
				: 'to_do'
	);

	function updateStepStatus(i: number) {
		return async () => {
			steps = steps.map((s, idx) =>
				idx === i
					? { ...s, status: s.status === 'done' ? 'in_progress' : 'done' }
					: s
			);
			actionsOpen[i] = false;
		};
	}

</script>

<div class="p-5 {accent_color}">
	<div class="rounded-lg bg-white p-4 flex flex-col justify-between h-full">
		<div class="flex justify-between mb-2">
			<div class="font-semibold">{title}</div>
			<div class="text-xl" title={safeTranslate(workshopStatus())}>
				{#if workshopStatus() == 'to_do'}
					<i class="fa-solid fa-exclamation"></i>
				{:else if workshopStatus() == 'in_progress'}
					<i class="fa-solid fa-spinner"></i>
				{:else if workshopStatus() == 'done'}
					<i class="fa-solid fa-check"></i>
				{/if}
			</div>
		</div>

		{@render action?.()}

		{#if content}
			{@render content()}
		{:else if meta}
			<div class="flex mx-auto">
				<div>
					<ol class="relative text-gray-500 border-s border-gray-200">
						{#each steps as step, i}
							<li class="flex flex-row justify-between mb-10 ms-6">
								{#if createRiskAnalysis && i == 0}
									{@render addRiskAnalysis?.()}
								{:else if !step.disabled}
									<Anchor
										href={step.href}
										prefixCrumbs={[{ label: safeTranslate(`ebiosWs${workshop}`) }]}
										label={safeTranslate(`ebiosWs${workshop}_${i + 1}`)}
										class="hover:text-purple-800"
									>
										{#if step.status == 'done'}
											<span
												class="absolute flex items-center justify-center w-8 h-8 bg-success-200 rounded-full -start-4 ring-4 ring-white"
											>
												<i class="fa-solid fa-check"></i>
											</span>
										{:else}
											<span
												class="absolute flex items-center justify-center w-8 h-8 bg-surface-200 rounded-full -start-4 ring-4 ring-white"
											>
												<i class="fa-solid fa-clipboard-check"></i>
											</span>
										{/if}
										<h3 class="font-medium leading-tight">{m.activity()} {i + 1}</h3>
										<p class="text-sm">{step.title}</p>
									</Anchor>
								{:else}
									<Tooltip
										open={open[i]}
										onOpenChange={(e) => (open[i] = e.open)}
										openDelay={0}
										zIndex="100"
									>
										{#snippet trigger()}
											<div class="text-gray-300 *:pointer-events-none">
												<span
													class="absolute flex items-center justify-center w-8 h-8 bg-surface-200 rounded-full -start-4 ring-4 ring-white"
												>
													<i class="fa-solid fa-clipboard-check"></i>
												</span>
												<h3 class="font-medium leading-tight text-start">{m.activity()} {i + 1}</h3>
												<p class="text-sm text-start">{step.title}</p>
											</div>
										{/snippet}
										{#snippet content()}
											<div class="transition card bg-white shadow-lg p-4 z-20 duration-300">
												<p
													data-testid="activity-tooltip"
													class="border-l-4 {borderColor} text-gray-500 p-2"
												>
													{step.tooltip}
												</p>
												<div class="arrow bg-white"></div>
											</div>
										{/snippet}
									</Tooltip>
								{/if}

								{#if !step.disabled}
									<Popover open={actionsOpen[i]} onOpenChange={(e) => (actionsOpen[i] = e.open)}>
										{#snippet trigger()}
											<button class="btn bg-initial" data-testid="sidebar-more-btn">
												<i class="fa-solid fa-ellipsis-vertical"></i>
											</button>
										{/snippet}
										{#snippet content()}
											<div
												class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1"
												data-testid="sidebar-more-panel"
											>
												<form
													action="/ebios-rm/{page.params.id}?/changeStepState"
													method="POST"
													use:enhance={updateStepStatus(i)}
												>
													<input type="hidden" name="workshop" value={workshop} />
													<input type="hidden" name="step" value={i + 1} />
													<input
														type="hidden"
														name="status"
														value={step.status === 'done' ? 'in_progress' : 'done'}
													/>
													<button type="submit" class="btn bg-initial">
														{step.status === 'done' ? m.markAsInProgress() : m.markAsDone()}
													</button>
												</form>
											</div>
										{/snippet}
									</Popover>
								{/if}
							</li>
						{/each}
					</ol>
				</div>
			</div>
		{/if}

		<div class="justify-end flex"></div>
	</div>
</div>
