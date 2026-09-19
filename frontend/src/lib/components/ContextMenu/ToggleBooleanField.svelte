<script lang="ts">
	import { page } from '$app/stores';
	import { getModelInfo } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { getFlash } from 'sveltekit-flash-message';

	/**
	 * Flip a boolean field on one row, in one click.
	 *
	 * ChangeChoiceField opens a submenu and asks which value you want, which is an
	 * extra step when there are only two and you always want the other one. The
	 * labels name the *action offered*, so they read as verbs rather than states.
	 */
	interface Props {
		row: any;
		handler: DataHandler;
		URLModel: string;
		action: {
			props: {
				field: string;
				// Offered when the field is currently true / currently false.
				labelWhenTrue: string;
				labelWhenFalse: string;
				iconWhenTrue?: string;
				iconWhenFalse?: string;
			};
		};
	}

	let { row, handler, URLModel, action }: Props = $props();
	const { field, labelWhenTrue, labelWhenFalse, iconWhenTrue, iconWhenFalse } = action.props;
	const flash = getFlash(page);

	const current = $derived(Boolean(row?.meta?.[field]));
	const label = $derived(safeTranslate(current ? labelWhenTrue : labelWhenFalse));
	const icon = $derived(
		(current ? iconWhenTrue : iconWhenFalse) ?? 'fa-solid fa-arrow-right-arrow-left'
	);
	const objectLabel = $derived(
		safeTranslate(getModelInfo(URLModel)?.localName ?? URLModel).toLowerCase()
	);

	async function toggle() {
		try {
			const res = await fetch(`/${URLModel}/${row?.meta?.id}/${field}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ [field]: !current })
			});
			if (!res.ok) throw new Error(String(res.status));
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: objectLabel })
			});
			handler.invalidate();
		} catch (error) {
			flash.set({ type: 'error', message: m.errorUpdatingObject({ object: objectLabel }) });
			console.error(`Error toggling ${field}:`, error);
		}
	}
</script>

<ContextMenu.Item
	class="flex h-10 select-none items-center rounded-base py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-muted cursor-pointer"
	onclick={toggle}
>
	<div class="flex items-center">
		<i class="{icon} mr-2 text-surface-500"></i>
		{label}
	</div>
</ContextMenu.Item>
