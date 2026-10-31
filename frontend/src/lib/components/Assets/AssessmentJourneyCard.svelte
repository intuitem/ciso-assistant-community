<script lang="ts">
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { gotoOrLoad } from '#lib/utils/breadcrumbs.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';

	interface Props {
		assetId: string;
	}

	let { assetId }: Props = $props();

	type Option = { kind: 'form' | 'publication'; id: string; name: string };
	type Journey = { response: { status: string } | null };

	let journey: Journey | null = $state(null);
	let options: Option[] = $state([]);
	let choosing = $state(false);
	let starting = $state(false);
	const toastStore = getToastStore();

	$effect(() => {
		// Aborted when the asset changes, so a late answer cannot land on another one.
		const controller = new AbortController();
		fetch(`/assets/${assetId}/assessment-journey`, { signal: controller.signal })
			.then((res) => (res.ok ? res.json() : { journey: null, options: [] }))
			.then((body) => {
				journey = body.journey;
				options = Array.isArray(body.options) ? body.options : [];
			})
			.catch(() => {});
		return () => controller.abort();
	});

	const draft = $derived(journey?.response?.status === 'draft');
	const startLabel = $derived(
		draft ? m.resumeFraming() : journey?.response ? m.newFraming() : m.startFraming()
	);

	function startFraming() {
		if (options.length === 1) start(options[0]);
		else choosing = !choosing;
	}

	// One start at a time: a double click must not open two drafts.
	async function start(option: Option) {
		if (starting) return;
		starting = true;
		try {
			const res = await fetch(`/assets/${assetId}/assessment-journey`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ kind: option.kind, id: option.id })
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok || !body.redirect) {
				toastStore.trigger({
					message: body.error ? safeTranslate(body.error) : m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			await gotoOrLoad(body.redirect);
		} catch {
			toastStore.trigger({ message: m.anErrorOccurred(), background: 'preset-filled-error-500' });
		} finally {
			starting = false;
		}
	}
</script>

{#if options.length > 0}
	<div class="space-y-2" data-testid="assessment-journey">
		<button
			type="button"
			class="btn btn-sm preset-filled-primary-500"
			disabled={starting}
			onclick={startFraming}
			data-testid="start-framing">{startLabel}</button
		>
		{#if choosing && options.length > 1}
			<ul class="space-y-1">
				{#each options as option (option.kind + option.id)}
					<li>
						<button type="button" class="anchor text-sm" onclick={() => start(option)}
							>{option.name}</button
						>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
{/if}
