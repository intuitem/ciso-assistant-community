<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { ruleLabel } from '#lib/components/QuickForms/rule-label.js';
	import { getLocale } from '#paraglide/runtime.js';
	import Anchor from '#lib/components/Anchor/Anchor.svelte';

	interface Props {
		staircase: Record<string, any>;
		rule: Record<string, any>;
		groups: Record<string, any>[];
	}

	let { staircase, rule, groups }: Props = $props();

	const levels = $derived((rule.levels ?? []).map(String) as string[]);
	const unitLabel = $derived(
		rule.translations?.[getLocale()]?.unit_label || rule.unit_label || m.staircaseSections()
	);
	const groupName = (id: string) => groups.find((g) => g.ref_id === id)?.name || id;
	const levelName = (level: number) =>
		level === 0 ? (rule.floor_label ?? '0') : groupName(levels[level - 1]);

	const STATUS: Record<string, { icon: string; color: string; label: () => string }> = {
		met: {
			icon: 'fa-solid fa-circle-check',
			color: 'text-success-600-400',
			label: () => m.staircaseMet()
		},
		not_met: {
			icon: 'fa-solid fa-circle-xmark',
			color: 'text-error-600-400',
			label: () => m.staircaseNotMet()
		},
		pending: {
			icon: 'fa-solid fa-circle-half-stroke',
			color: 'text-warning-600-400',
			label: () => m.staircasePending()
		},
		out_of_scope: {
			icon: 'fa-solid fa-minus',
			color: 'text-surface-400-600',
			label: () => m.staircaseOutOfScope()
		}
	};
</script>

<div class="space-y-4">
	<div
		class="flex items-center gap-4 rounded-xl border border-surface-200-800 bg-surface-100-900 p-4"
	>
		<div
			class="flex items-center justify-center w-12 h-12 rounded-xl bg-primary-500 text-white text-2xl font-bold tabular-nums shrink-0"
		>
			{staircase.level}
		</div>
		<div class="flex flex-col">
			<span class="text-xs uppercase tracking-wide text-surface-600-400"
				>{ruleLabel(rule, rule.ref_id)}</span
			>
			<span class="text-lg font-semibold text-surface-900-50">{levelName(staircase.level)}</span>
			{#if staircase.units.length > 1}
				<span class="text-xs text-surface-600-400"
					>{m.staircaseOverall({ count: staircase.units.length, unit: unitLabel })}</span
				>
			{/if}
		</div>
	</div>

	<div class="overflow-x-auto">
		<table class="w-full text-sm">
			<thead>
				<tr class="text-left text-xs uppercase tracking-wide text-surface-600-400">
					<th class="py-2 pr-3 font-medium"></th>
					{#each levels as level (level)}
						<th class="py-2 px-2 font-medium text-center">{groupName(level)}</th>
					{/each}
					<th class="py-2 pl-3 font-medium text-right">{ruleLabel(rule, rule.ref_id)}</th>
				</tr>
			</thead>
			<tbody>
				{#each staircase.units as unit (unit.node_id)}
					<tr class="border-t border-surface-200-800 align-top">
						<td class="py-2 pr-3">
							<div class="font-medium text-surface-900-50">
								{unit.name ?? ruleLabel(rule, rule.ref_id)}
							</div>
							{#if unit.blocking.length}
								<details class="mt-1">
									<summary class="cursor-pointer text-xs text-surface-600-400">
										{m.staircaseBlocking({ count: unit.blocking.length })}
									</summary>
									<ul class="mt-1 space-y-0.5">
										{#each unit.blocking as item (item.urn)}
											<li class="flex items-baseline gap-2 text-xs">
												<i
													class="{STATUS[item.result === 'not_assessed' ? 'pending' : 'not_met']
														.icon} {STATUS[item.result === 'not_assessed' ? 'pending' : 'not_met']
														.color} shrink-0"
													aria-hidden="true"
												></i>
												{#if item.id}
													<Anchor
														breadcrumbAction="push"
														href={`/requirement-assessments/${item.id}`}
														class="anchor">{item.ref_id ?? item.name}</Anchor
													>
												{:else}
													<span>{item.ref_id ?? item.name}</span>
												{/if}
												<span class="text-surface-600-400">{safeTranslate(item.result ?? '')}</span>
											</li>
										{/each}
									</ul>
								</details>
							{/if}
						</td>
						{#each levels as level (level)}
							{@const status = STATUS[unit.levels[level]] ?? STATUS.out_of_scope}
							<td class="py-2 px-2 text-center">
								<i class="{status.icon} {status.color}" title={status.label()} aria-hidden="true"
								></i>
								<span class="sr-only">{status.label()}</span>
								{#if unit.levels[level] !== 'out_of_scope' && unit.progress?.[level]}
									<div class="text-[11px] tabular-nums text-surface-600-400">
										{unit.progress[level][0]}/{unit.progress[level][1]}
									</div>
								{/if}
							</td>
						{/each}
						<td class="py-2 pl-3 text-right whitespace-nowrap">
							<span
								class="inline-flex items-center justify-center min-w-7 h-7 px-2 rounded-lg font-semibold tabular-nums {unit.level ===
								staircase.level
									? 'bg-primary-500 text-white'
									: 'bg-surface-200-800 text-surface-900-50'}"
								title={levelName(unit.level)}>{unit.level}</span
							>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
