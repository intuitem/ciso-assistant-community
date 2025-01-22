<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { ContextMenu } from 'bits-ui';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import * as m from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';
	import { browser } from '$app/environment';
	import { popup, type PopupSettings } from '@skeletonlabs/skeleton';

	export let title = 'activity';
	export let meta: Record<string, any>[] = [];
	export let accent_color = '';
	export let borderColor = '';
	export let createRiskAnalysis = false;

	let openMenuIndex: number | null = null;
	export let workshop: number = 0;

	let workshopStatus = 'to_do';

	$: {
		workshopStatus = meta.every((step) => step.status === 'done')
			? 'done'
			: meta.some((step) => step.status === 'done')
				? 'in_progress'
				: 'to_do';
		if (browser) invalidateAll();
	}

	let popupHover: PopupSettings[] = [];
	for (let i = 0; i < meta.length; i++) {
		popupHover.push({
			event: 'hover',
			target: 'popup' + workshop + i,
			placement: 'top'
		});
	}
</script>

<div class="p-5 {accent_color}">
	<div class="rounded-lg bg-white p-4 flex flex-col justify-between h-full">
		<div class="flex justify-between mb-2">
			<div class="font-semibold">{title}</div>
			<div class="text-xl" title={safeTranslate(workshopStatus)}>
				{#if workshopStatus == 'to_do'}
					<i class="fa-solid fa-exclamation"></i>
				{:else if workshopStatus == 'in_progress'}
					<i class="fa-solid fa-spinner"></i>
				{:else if workshopStatus == 'done'}
					<i class="fa-solid fa-check"></i>
				{/if}
			</div>
		</div>
		<slot name="content">
			{#if meta}
				<div class="flex mx-auto">
					<div>
						<ol class="relative text-gray-500 border-s border-gray-200">
							{#each meta as step, i}
								<li class="flex flex-row justify-between mb-10 ms-6">
									{#if createRiskAnalysis && i == 0}
										<slot name="addRiskAnalysis"></slot>
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
													<i class="fa-solid fa-check" />
												</span>
											{:else}
												<span
													class="absolute flex items-center justify-center w-8 h-8 bg-surface-200 rounded-full -start-4 ring-4 ring-white"
												>
													<i class="fa-solid fa-clipboard-check" />
												</span>
											{/if}
											<h3 class="font-medium leading-tight">{m.activity()} {i + 1}</h3>
											<p class="text-sm">{step.title}</p>
										</Anchor>
									{:else}
										<div class="text-gray-300 [&>*]:pointer-events-none" use:popup={popupHover[i]}>
											<div
												class="transition card bg-white shadow-lg p-4 z-20 duration-300"
												data-popup={'popup' + workshop + i}
											>
												<p
													data-testid="activity-tooltip"
													class="border-l-4 {borderColor} text-gray-500 p-2"
												>
													{step.tooltip}
												</p>
												<div class="arrow bg-white" />
											</div>
											<span
												class="absolute flex items-center justify-center w-8 h-8 bg-surface-200 rounded-full -start-4 ring-4 ring-white"
											>
												<i class="fa-solid fa-clipboard-check" />
											</span>
											<h3 class="font-medium leading-tight">{m.activity()} {i + 1}</h3>
											<p class="text-sm">{step.title}</p>
										</div>
									{/if}
									{#if !step.disabled}
										<button
											class="btn bg-initial"
											data-testid="sidebar-more-btn"
											use:popup={{
												event: 'click',
												target: `popupStep-${workshop}.${i + 1}`,
												placement: 'top'
											}}><i class="fa-solid fa-ellipsis-vertical" /></button
										>
										<div
											class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1"
											data-testid="sidebar-more-panel"
											data-popup="popupStep-{workshop}.{i + 1}"
										>
											<form
												action="/ebios-rm/{$page.params.id}?/changeStepState"
												method="POST"
												use:enhance={() => {
													return async () => {
														if (step.status !== 'done') step.status = 'done';
														else step.status = 'in_progress';
													};
												}}
											>
												<input type="hidden" name="workshop" value={workshop} />
												<input type="hidden" name="step" value={i + 1} />
												{#if step.status === 'done'}
													<input type="hidden" name="status" value="in_progress" />
													<button type="submit" class="btn bg-initial"
														>{m.markAsInProgress()}</button
													>
												{:else}
													<input type="hidden" name="status" value="done" />
													<button type="submit" class="btn bg-initial">{m.markAsDone()}</button>
												{/if}
											</form>
										</div>
									{/if}
								</li>
							{/each}
						</ol>
					</div>
				</div>
			{/if}
		</slot>
		<div class="justify-end flex"></div>
	</div>
</div>
