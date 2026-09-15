<script lang="ts">
	import {
		CATEGORY_META,
		EVENT_TYPES,
		SEVERITY_META,
		categoryOf,
		isConditionBacked,
		type Notif
	} from './fixtures';
	import { relTime, shortDate } from './time';

	interface Props {
		n: Notif;
		selected: boolean;
		objectFixed: boolean;
		onToggleSelect: () => void;
		onOpen: () => void;
		onToggleRead: () => void;
		onDelete: () => void;
		onToggleFixed: () => void;
	}
	let {
		n,
		selected,
		objectFixed,
		onToggleSelect,
		onOpen,
		onToggleRead,
		onDelete,
		onToggleFixed
	}: Props = $props();

	const conditionBacked = $derived(isConditionBacked(n));
	const category = $derived(CATEGORY_META[categoryOf(n)]);
</script>

<tr
	class="hover:bg-surface-100-900 transition-colors {n.isRead
		? 'bg-surface-50-950'
		: 'bg-primary-50/40 dark:bg-primary-950/30'}"
>
	<td class="p-3 align-top">
		<input
			type="checkbox"
			class="checkbox"
			checked={selected}
			onchange={onToggleSelect}
			aria-label="Select notification"
		/>
	</td>

	<td class="p-3">
		<div class="flex gap-2.5">
			<span class="mt-1.5 size-2 shrink-0 rounded-full {SEVERITY_META[n.severity].dot}"></span>
			<div class="min-w-0">
				<button
					class="text-left cursor-pointer {n.isRead
						? 'font-normal text-surface-700-300'
						: 'font-bold text-surface-900-100'}"
					onclick={onOpen}
				>
					{n.title}
				</button>
				<p class="text-surface-500 mt-0.5">{n.body}</p>
				<div class="flex flex-wrap items-center gap-1.5 mt-1.5">
					<a
						href={n.link}
						class="text-primary-600 hover:underline"
						onclick={(e) => e.preventDefault()}
					>
						<i class="fa-solid fa-arrow-up-right-from-square mr-1 text-[10px]"></i>{n.linkLabel}
					</a>
					{#if n.attestation}
						<a
							href={n.attestation.link}
							class="px-2 py-0.5 rounded border border-primary-300 dark:border-primary-700 text-primary-700 dark:text-primary-300 hover:bg-primary-50 dark:hover:bg-primary-950"
							onclick={(e) => e.preventDefault()}
							title="The record lives on the object, never in the inbox"
						>
							{n.attestation.label} →
						</a>
					{/if}
					{#if n.seenCount > 1}
						<span
							class="px-1.5 py-0.5 rounded bg-surface-100-900 border border-surface-200-800 text-surface-500"
							title="One row, upserted by every sweep — not {n.seenCount} rows"
						>
							reminded {n.seenCount}× since {shortDate(n.createdAt)}
						</span>
					{/if}
					{#if n.autoClearedAt}
						<span
							class="px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
							title="The sweep saw the condition go away, marked this read and released the dedupe key"
						>
							<i class="fa-solid fa-check mr-1"></i>no longer applies
						</span>
					{/if}
					{#if objectFixed && !n.autoClearedAt}
						<span
							class="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
						>
							object fixed — clears on next sweep
						</span>
					{/if}
					{#if !conditionBacked}
						<span
							class="px-1.5 py-0.5 rounded bg-surface-100-900 border border-surface-200-800 text-surface-400"
							title="No dedupe key: fires once, never auto-clears"
						>
							event
						</span>
					{/if}
				</div>
			</div>
		</div>
	</td>

	<td class="p-3 align-top text-surface-600-400">
		<i class="fa-solid {category.icon} mr-1.5 text-surface-400"></i>
		<span class="block">{EVENT_TYPES[n.type].label}</span>
		<span class="block text-[10px] text-surface-400">{category.label}</span>
	</td>

	<td class="p-3 align-top text-surface-600-400 whitespace-nowrap">
		<i class="fa-solid fa-sitemap mr-1 text-surface-400"></i>{n.folder}
	</td>

	<td class="p-3 align-top text-surface-500 whitespace-nowrap">{relTime(n.lastSeenAt)}</td>

	<td class="p-3 align-top">
		<div class="flex items-center justify-end gap-1">
			{#if conditionBacked}
				<button
					class="size-7 rounded hover:bg-surface-200-800 cursor-pointer {objectFixed
						? 'text-amber-600'
						: 'text-surface-500'}"
					title={objectFixed ? 'Un-fix the object' : 'Pretend the underlying object got fixed'}
					onclick={onToggleFixed}
				>
					<i class="fa-solid fa-wrench text-[11px]"></i>
				</button>
			{/if}
			<button
				class="size-7 rounded hover:bg-surface-200-800 text-surface-500 cursor-pointer"
				title={n.isRead ? 'Mark as unread — bring it back to me' : 'Mark as read'}
				onclick={onToggleRead}
			>
				<i class="fa-solid {n.isRead ? 'fa-envelope' : 'fa-envelope-open'} text-[11px]"></i>
			</button>
			<button
				class="size-7 rounded hover:bg-error-100 dark:hover:bg-error-950 text-surface-500 hover:text-error-600 cursor-pointer"
				title="Delete — removes the message and its dedupe key. If the condition still holds it returns tomorrow."
				onclick={onDelete}
			>
				<i class="fa-solid fa-trash text-[11px]"></i>
			</button>
		</div>
	</td>
</tr>
