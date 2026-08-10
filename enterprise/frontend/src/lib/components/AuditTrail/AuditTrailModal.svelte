<script lang="ts">
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime.js';
	import { onMount } from 'svelte';

	type M2MChange = { type: 'm2m'; operation: string; objects: string[] };

	interface AuditEntry {
		id: number;
		cid: string | null;
		action: string;
		actor: string | null;
		timestamp: string;
		changes: Record<string, [unknown, unknown] | M2MChange> | string | null;
	}

	interface AuditEvent {
		key: string;
		action: string;
		actor: string | null;
		timestamp: string;
		changes: { field: string; from: unknown; to: unknown }[];
	}

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		model: string;
		objectId: string;
	}

	let { parent, model, objectId }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-surface-50-950 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	let entries: AuditEntry[] = $state([]);
	let loading = $state(true);
	let errorMessage: string | null = $state(null);

	const actionVariant = (action: string): string => {
		switch (action.toLowerCase()) {
			case 'create':
				return 'preset-tonal-success';
			case 'delete':
				return 'preset-tonal-error';
			case 'update':
				return 'preset-tonal-primary';
			default:
				return 'preset-tonal-surface';
		}
	};

	const isM2M = (value: unknown): value is M2MChange =>
		!!value && typeof value === 'object' && !Array.isArray(value) && (value as any).type === 'm2m';

	// Group entries by correlation id (one card per save); a null cid stands alone.
	const groupEvents = (raw: AuditEntry[]): AuditEvent[] => {
		const order: string[] = [];
		const byKey = new Map<
			string,
			{
				event: AuditEvent;
				scalar: Map<string, { from: unknown; to: unknown }>;
				m2m: Map<string, { deleted: string[]; added: string[] }>;
			}
		>();

		for (const e of raw) {
			const key = e.cid ?? `id:${e.id}`;
			let g = byKey.get(key);
			if (!g) {
				g = {
					event: { key, action: e.action, actor: e.actor, timestamp: e.timestamp, changes: [] },
					scalar: new Map(),
					m2m: new Map()
				};
				byKey.set(key, g);
				order.push(key);
			}
			if (e.action?.toLowerCase() === 'create') g.event.action = e.action;

			const changes = e.changes;
			if (changes && typeof changes === 'object') {
				for (const [field, value] of Object.entries(changes)) {
					if (isM2M(value)) {
						let acc = g.m2m.get(field);
						if (!acc) {
							acc = { deleted: [], added: [] };
							g.m2m.set(field, acc);
						}
						const objs = Array.isArray(value.objects) ? value.objects : [];
						if (value.operation === 'delete') acc.deleted.push(...objs);
						else acc.added.push(...objs);
					} else if (!g.scalar.has(field)) {
						g.scalar.set(field, {
							from: Array.isArray(value) ? value[0] : undefined,
							to: Array.isArray(value) ? value[1] : undefined
						});
					}
				}
			}
		}

		return order.map((key) => {
			const g = byKey.get(key)!;
			const changes = [
				...[...g.scalar.entries()].map(([field, v]) => ({ field, from: v.from, to: v.to })),
				...[...g.m2m.entries()].map(([field, v]) => ({
					field,
					from: v.deleted.length ? v.deleted : undefined,
					to: v.added.length ? v.added : undefined
				}))
			];
			return { ...g.event, changes };
		});
	};

	const events = $derived(groupEvents(entries));

	const fmt = (value: unknown): string => {
		if (Array.isArray(value)) {
			return value.length ? value.map((v) => safeTranslate(String(v))).join(', ') : '∅';
		}
		if (value === null || value === undefined || value === '') return '∅';
		const s = String(value);
		// Pretty-print embedded JSON (e.g. field_visibility) so it wraps readably.
		const trimmed = s.trim();
		if (/^[[{]/.test(trimmed) && /[\]}]$/.test(trimmed)) {
			try {
				return JSON.stringify(JSON.parse(trimmed), null, 2);
			} catch {
				/* not JSON, fall through */
			}
		}
		return safeTranslate(s);
	};

	onMount(async () => {
		try {
			const res = await fetch(`/fe-api/audit-trail/${model}/${objectId}`);
			if (!res.ok) {
				errorMessage = res.status === 403 ? m.permissionDenied() : m.couldNotLoadAuditTrail();
				return;
			}
			entries = await res.json();
		} catch (e) {
			errorMessage = m.couldNotLoadAuditTrail();
		} finally {
			loading = false;
		}
	});
</script>

{#if $modalStore[0]}
	<div class={cBase}>
		<header class={cHeader}>{$modalStore[0].title ?? m.auditTrail()}</header>

		<div class="max-h-[32rem] overflow-y-auto">
			{#if loading}
				<p class="text-surface-500">{m.loading()}…</p>
			{:else if errorMessage}
				<p class="text-error-500">{errorMessage}</p>
			{:else if events.length === 0}
				<p class="text-surface-500">{m.noHistoryForThisObject()}</p>
			{:else}
				<ul class="space-y-6">
					{#each events as event (event.key)}
						<li class="border-l-2 border-surface-300-700 pl-4 py-1">
							<div class="flex items-center gap-2 flex-wrap">
								<span class="badge {actionVariant(event.action)}"
									>{safeTranslate(event.action)}</span
								>
								<span class="font-semibold">{event.actor ?? m.system()}</span>
								<span class="text-surface-500 text-sm"
									>{formatDateOrDateTime(event.timestamp, getLocale())}</span
								>
							</div>
							{#if event.changes.length > 0}
								<div class="mt-3 space-y-2 text-sm">
									{#each event.changes as change (change.field)}
										<div class="grid grid-cols-[10rem_minmax(0,1fr)] gap-x-3 gap-y-0.5 items-start">
											<div class="font-medium text-surface-600-400 break-words">
												{safeTranslate(change.field)}
											</div>
											<div class="flex flex-wrap items-start gap-x-2 gap-y-1 min-w-0">
												<span class="text-error-700-300 whitespace-pre-wrap break-words min-w-0"
													>{fmt(change.from)}</span
												>
												<span class="text-surface-400 shrink-0">→</span>
												<span class="text-success-700-300 whitespace-pre-wrap break-words min-w-0"
													>{fmt(change.to)}</span
												>
											</div>
										</div>
									{/each}
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</div>

		<footer class="flex justify-end">
			<button type="button" class="btn preset-tonal-surface" onclick={() => modalStore.close()}>
				{m.close()}
			</button>
		</footer>
	</div>
{/if}
