<script lang="ts">
	import { m } from '$paraglide/messages';
	import IconPicker from '$lib/components/IconPicker/IconPicker.svelte';
	import VisibilityEditor from '$lib/components/ComplianceAssessment/VisibilityEditor.svelte';

	type Item = {
		id?: string;
		icon: string;
		title: string;
		description: string;
		kind: string;
		target: Record<string, any>;
	};

	let {
		item,
		ctx,
		sections,
		si,
		ii,
		onMoveItem,
		onRemoveItem,
		onMoveToGroup,
		onUpload
	}: {
		item: Item;
		ctx: any;
		sections: { title: string }[];
		si: number;
		ii: number;
		onMoveItem: (dir: -1 | 1) => void;
		onRemoveItem: () => void;
		onMoveToGroup: (targetSi: number) => void;
		onUpload: (item: Item, e: Event) => void;
	} = $props();

	function toggleIg(refId: string) {
		const list: string[] = item.target.implementation_groups ?? [];
		item.target.implementation_groups = list.includes(refId)
			? list.filter((r) => r !== refId)
			: [...list, refId];
	}

	function targetField(kind: string) {
		if (kind === 'create') return { key: 'model', label: 'Model (url name)', ph: 'incidents' };
		if (kind === 'navigate') return { key: 'model', label: 'Model (url name)', ph: '' };
		if (kind === 'metric') return { key: 'value', label: m.value(), ph: '128' };
		if (kind === 'certificationDocument') return { key: '', label: m.proof(), ph: '' };
		if (kind === 'framework') return { key: 'snapshot', label: m.framework(), ph: '' };
		if (kind === 'assessment') return { key: '', label: 'Audit setup', ph: '' };
		return { key: 'url', label: 'URL', ph: kind === 'external' ? 'https://…' : '/incidents' };
	}

	const tf = $derived(targetField(item.kind));
	const fw = $derived(ctx.frameworks.find((f: any) => f.id === item.target.framework));
</script>

<div class="flex flex-wrap items-end gap-2 rounded-lg border border-surface-200-800 p-3">
	<label class="text-[10px] text-surface-500">
		<span class="block">Icon</span>
		<IconPicker bind:value={item.icon} showInput={false} />
	</label>
	<label class="text-[10px] text-surface-500 grow">
		<span class="block">{m.title()}</span>
		<input bind:value={item.title} class="input rounded-md text-sm" />
	</label>
	<label class="text-[10px] text-surface-500">
		<span class="block">Kind</span>
		<select bind:value={item.kind} class="select rounded-md text-sm">
			{#each ctx.kinds as k}<option value={k}>{ctx.kindLabels[k] ?? k}</option>{/each}
		</select>
	</label>
	<label class="text-[10px] text-surface-500 grow">
		<span class="block">{tf.label}</span>
		{#if item.kind === 'create'}
			<select bind:value={item.target.model} class="select rounded-md text-sm">
				<option value="">—</option>
				{#each ctx.modelOptions as o}<option value={o.value}>{o.label}</option>{/each}
			</select>
		{:else if item.kind === 'navigate'}
			<select bind:value={item.target.model} required class="select rounded-md text-sm">
				<optgroup label="Models">
					{#each ctx.modelOptions as o}<option value={o.value}>{o.label}</option>{/each}
				</optgroup>
				<optgroup label="Pages">
					{#each ctx.pageDestinations as p}<option value={p.value}>{p.label}</option>{/each}
				</optgroup>
			</select>
		{:else if item.kind === 'certificationDocument'}
			<input
				bind:value={item.target.image_url}
				placeholder={m.imageUrlOptional()}
				class="input rounded-md text-sm"
			/>
			<div class="mt-1 flex gap-1">
				<input
					type="date"
					bind:value={item.target.valid_from}
					class="input rounded-md text-sm"
					title={m.validFrom()}
				/>
				<input
					type="date"
					bind:value={item.target.valid_until}
					class="input rounded-md text-sm"
					title={m.validUntil()}
				/>
			</div>
			<select bind:value={item.target.dest} class="select mt-1 rounded-md text-sm">
				<option value="link">{m.link()}</option>
				<option value="document">{m.file()}</option>
			</select>
			{#if item.target.dest === 'document'}
				<div class="flex items-center gap-1">
					<select bind:value={item.target.token} class="select mt-1 grow rounded-md text-sm">
						<option value="">—</option>
						{#each ctx.docs as d}<option value={d.token}>{d.name}</option>{/each}
					</select>
					<label
						class="mt-1 flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-md border border-surface-200-800 text-violet-500 hover:bg-surface-100-900"
						title={m.uploadNewFile()}
					>
						<i class="fa-solid fa-upload text-xs"></i>
						<input type="file" class="hidden" onchange={(e) => onUpload(item, e)} />
					</label>
				</div>
			{:else}
				<input
					bind:value={item.target.url}
					placeholder="https://..."
					class="input mt-1 rounded-md text-sm"
				/>
			{/if}
		{:else if item.kind === 'framework'}
			<select bind:value={item.target.snapshot} class="select rounded-md text-sm">
				<option value="">—</option>
				{#each ctx.snapshots as s}<option value={s.id}>{s.name} ({s.framework_name})</option>{/each}
			</select>
		{:else if item.kind === 'metric'}
			<select bind:value={item.target.source} class="select rounded-md text-sm">
				{#each ctx.metricSources as src}<option value={src.value}>{src.label}</option>{/each}
			</select>
			{#if !item.target.source}
				<input
					bind:value={item.target.value}
					placeholder="128"
					class="input mt-1 rounded-md text-sm"
				/>
			{/if}
		{:else if item.kind === 'assessment'}
			<select bind:value={item.target.framework} required class="select rounded-md text-sm">
				<option value="">{m.framework()}…</option>
				{#each ctx.frameworks as f}<option value={f.id}>{f.name}</option>{/each}
			</select>
			<div class="mt-1 flex gap-1">
				<select bind:value={item.target.folder} required class="select grow rounded-md text-sm">
					<option value="">{m.userChoosesDomain()}</option>
					{#each ctx.folders as d}<option value={d.id}>{d.name}</option>{/each}
				</select>
				<select bind:value={item.target.mode} class="select rounded-md text-sm">
					<option value="full">{m.fullAudit()}</option>
					<option value="auditee">{m.auditeeMode()}</option>
				</select>
			</div>
			{#if fw && fw.implementation_groups_definition.length}
				<div class="mt-1 flex flex-wrap gap-x-3 gap-y-1">
					{#each fw.implementation_groups_definition as ig}
						<label class="flex items-center gap-1 text-[10px] text-surface-600-400">
							<input
								type="checkbox"
								class="checkbox"
								checked={(item.target.implementation_groups ?? []).includes(ig.ref_id)}
								onchange={() => toggleIg(ig.ref_id)}
							/>
							{ig.name ?? ig.ref_id}
						</label>
					{/each}
				</div>
			{/if}
		{:else}
			<input
				bind:value={item.target[tf.key]}
				placeholder={tf.ph}
				class="input rounded-md text-sm"
			/>
		{/if}
	</label>
	<label class="text-[10px] text-surface-500">
		<span class="block">Group</span>
		<select
			value={si}
			onchange={(e) => onMoveToGroup(+e.currentTarget.value)}
			class="select rounded-md text-sm"
		>
			{#each sections as s, gi}<option value={gi}>{s.title || `Group ${gi + 1}`}</option>{/each}
		</select>
	</label>
	<label class="text-[10px] text-surface-500 w-full">
		<span class="block">Description (markdown)</span>
		<textarea bind:value={item.description} rows="2" class="textarea rounded-md text-sm w-full"
		></textarea>
	</label>
	{#if item.kind === 'assessment'}
		<div class="w-full space-y-2 border-t border-surface-200-800 pt-2">
			<label class="flex items-center gap-2 text-[10px] text-surface-600-400">
				<input type="checkbox" class="checkbox" bind:checked={item.target.user_names} />
				{m.letUserNameAudit()}
			</label>
			<details class="text-[10px]">
				<summary class="cursor-pointer text-surface-500">{m.answeringVisibility()}</summary>
				<div class="mt-2">
					<VisibilityEditor
						value={item.target.field_visibility}
						frameworkDefaults={fw?.effective_field_visibility ?? null}
						onChange={(next) => (item.target.field_visibility = next)}
					/>
				</div>
			</details>
		</div>
	{/if}
	<div class="flex gap-1">
		<button
			onclick={() => onMoveItem(-1)}
			class="btn-icon btn-sm preset-tonal"
			aria-label="Move item up"><i class="fa-solid fa-chevron-up"></i></button
		>
		<button
			onclick={() => onMoveItem(1)}
			class="btn-icon btn-sm preset-tonal"
			aria-label="Move item down"><i class="fa-solid fa-chevron-down"></i></button
		>
		<button
			onclick={onRemoveItem}
			class="btn-icon btn-sm preset-tonal-error"
			aria-label={m.delete()}><i class="fa-solid fa-trash"></i></button
		>
	</div>
</div>
