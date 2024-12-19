<script lang="ts">
	import * as m from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { ContextMenu } from 'bits-ui';

	export let title = 'activity';
	export let status = '';
	export let meta = null;
	export let accent_color = '';
	export let createRiskAnalysis = false;

	let openMenuIndex: number | null = null;
</script>

<div class="p-5 {accent_color}">
	<div class="rounded-lg bg-white p-4 flex flex-col justify-between h-full">
		<div class="flex justify-between mb-2">
			<div class="font-semibold">{title}</div>
			<div class="text-xl" title={safeTranslate(status)}>
				{#if status == 'to_do'}
					<i class="fa-solid fa-exclamation"></i>
				{:else if status == 'in_progress'}
					<i class="fa-solid fa-spinner"></i>
				{:else if status == 'done'}
					<i class="fa-solid fa-check"></i>
				{/if}
			</div>
		</div>
		{#if meta}
			<div class="flex mx-auto">
				<div>
					<ol class="relative text-gray-500 border-s border-gray-200">
						{#each meta as step, i}
							<ContextMenu.Root
								open={openMenuIndex === i}
								onOpenChange={(isOpen) => (openMenuIndex = isOpen ? i : null)}
							>
								<ContextMenu.Trigger>
									<li class="mb-10 ms-6">
										<a href={step.href} class="hover:text-purple-800">
											<span
												class="absolute flex items-center justify-center w-8 h-8 {step.status ===
												'done'
													? 'bg-green-200'
													: 'bg-gray-100'} rounded-full -start-4 ring-4 ring-white"
											>
												<i
													class={step.status === 'done'
														? 'fa-solid fa-check'
														: 'fa-solid fa-clipboard-check'}
												></i>
											</span>
											<h3 class="font-medium leading-tight">{m.activity()} {i + 1}</h3>
											<p class="text-sm">{step.title}</p>
										</a>
									</li>
								</ContextMenu.Trigger>

								<ContextMenu.Content
									class="z-50 w-full max-w-[229px] rounded-xl bg-gray-700 text-white px-2 py-2 shadow-xl outline-none transition-all duration-300"
								>
									<ContextMenu.Item
										class="px-4 py-2 rounded-md text-base font-medium hover:bg-gray-600 transition-all duration-300 cursor-pointer"
										on:click={() => (step.status = step.status === 'done' ? '' : 'done')}
									>
										{#if step.status === 'done'}
											{m.markAsNotValid()}
										{:else}
											{m.markAsValid()}
										{/if}
									</ContextMenu.Item>
								</ContextMenu.Content>
							</ContextMenu.Root>
						{/each}
					</ol>
				</div>
			</div>
		{/if}
		<div class="justify-end flex"></div>
	</div>
</div>
