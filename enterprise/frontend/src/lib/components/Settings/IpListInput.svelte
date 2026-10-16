<script lang="ts">
	import { m } from '$paraglide/messages';
	import {
		isIpOrCidr,
		normalizeIpForCompare,
		IP_INPUT_MAXLENGTH,
		MAX_ALLOWED_IPS
	} from '$lib/utils/infra-config';

	interface Props {
		/** The list of IP addresses / CIDR ranges (use `bind:ips`). */
		ips?: string[];
		/** Prefix of the element ids and `data-testid`s (`<prefix>-input`, `<prefix>-list`, `<prefix>-chip`). */
		idPrefix?: string;
		/** Maximum number of entries in the list. */
		max?: number;
		/** Warning shown when the list contains `0.0.0.0/0` or `::/0` (matches every address). */
		allMatchWarning?: string;
		/** Text shown when the list is empty. */
		emptyText: string;
	}

	let {
		ips = $bindable([]),
		idPrefix = 'allowed-ip',
		max = MAX_ALLOWED_IPS,
		allMatchWarning = undefined,
		emptyText
	}: Props = $props();

	let newIp = $state('');
	let inputError = $state('');

	const matchesAll = $derived(ips.some((ip) => ['0.0.0.0/0', '::/0'].includes(ip.trim())));

	function addIp() {
		const ip = newIp.trim();
		if (!ip) {
			inputError = m.enterIpFirst();
			return;
		}
		if (ips.length >= max) {
			inputError = m.tooManyAllowedIps({ max });
			return;
		}
		if (!isIpOrCidr(ip)) {
			inputError = m.invalidIpOrCidr();
			return;
		}
		const norm = normalizeIpForCompare(ip);
		if (ips.some((existing) => normalizeIpForCompare(existing) === norm)) {
			inputError = m.ipAlreadyAdded();
			return;
		}
		ips = [...ips, ip];
		newIp = '';
		inputError = '';
	}

	function removeIp(index: number) {
		ips = ips.filter((_, i) => i !== index);
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addIp();
		}
	}
</script>

<div class="flex items-start gap-2">
	<div class="flex flex-col gap-1 w-full max-w-md">
		<input
			id="{idPrefix}-input"
			name="{idPrefix}-input"
			type="text"
			bind:value={newIp}
			onkeydown={onKeydown}
			oninput={() => (inputError = '')}
			placeholder={m.ipAddressOrCidr()}
			aria-label={m.ipAddressOrCidr()}
			aria-invalid={inputError ? 'true' : undefined}
			aria-describedby={inputError ? `${idPrefix}-error` : undefined}
			autocomplete="off"
			maxlength={IP_INPUT_MAXLENGTH}
			class="input font-mono {inputError ? 'border border-error-500' : ''}"
			data-testid="{idPrefix}-input"
		/>
		{#if inputError}
			<span id="{idPrefix}-error" class="text-error-500 text-xs">{inputError}</span>
		{/if}
	</div>
	<button
		type="button"
		class="btn preset-tonal-primary-500"
		onclick={addIp}
		disabled={ips.length >= max}
	>
		<i class="fa-solid fa-plus mr-1"></i>
		{m.add()}
	</button>
</div>

{#if allMatchWarning && matchesAll}
	<p class="text-warning-700-300 text-sm flex items-center gap-2">
		<i class="fa-solid fa-triangle-exclamation"></i>
		{allMatchWarning}
	</p>
{/if}

{#if ips.length > 0}
	<div class="flex flex-wrap gap-2 max-h-64 overflow-y-auto" data-testid="{idPrefix}-list">
		{#each ips as ip, i (ip)}
			<span
				class="badge preset-tonal-surface flex items-center gap-2 font-mono max-w-xs"
				data-testid="{idPrefix}-chip"
			>
				<span class="truncate">{ip}</span>
				<button
					type="button"
					aria-label={m.removeIp({ ip })}
					class="hover:text-error-500 cursor-pointer shrink-0"
					onclick={() => removeIp(i)}
				>
					<i class="fa-solid fa-xmark"></i>
				</button>
			</span>
		{/each}
	</div>
{:else}
	<p class="text-surface-500 italic">{emptyText}</p>
{/if}
