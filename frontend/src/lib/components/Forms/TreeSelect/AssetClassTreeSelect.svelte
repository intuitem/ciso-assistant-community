<script lang="ts">
	import { onMount } from 'svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import TreeSelect from './TreeSelect.svelte';
	import type { TreeSelectItem } from './TreeSelectNode.svelte';

	interface RawNode {
		id: string;
		name: string;
		/** Per-locale name, resolved server-side; falls back to `name`. */
		translated_name: string;
		builtin: boolean;
		is_visible: boolean;
		children: RawNode[];
	}

	interface Props {
		form: SuperForm<any>;
		field: string;
		label?: string;
		helpText?: string;
		disabled?: boolean;
		hidden?: boolean;
		cacheLock?: CacheLock;
		cachedValue?: any;
		onChange?: (value: any) => void;
		excludeSubtreeOf?: string | null;
		/** Raw name of the currently-linked class, for values missing from the tree. */
		fallbackLabel?: string | null;
		/** False lets the management form nest under a hidden class. */
		visibleOnly?: boolean;
	}

	let {
		form,
		field,
		label = undefined,
		helpText = undefined,
		disabled = false,
		hidden = false,
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x: any) => x
		},
		cachedValue = $bindable(),
		onChange = () => {},
		excludeSubtreeOf = null,
		fallbackLabel = null,
		visibleOnly = true
	}: Props = $props();

	let nodes = $state<TreeSelectItem[]>([]);
	let isLoading = $state(false);

	// Built-in names are i18n keys; custom ones are already translated
	// server-side and pass through safeTranslate unchanged.
	function normalise(raw: RawNode[]): TreeSelectItem[] {
		return raw.map((node) => ({
			id: node.id,
			label: safeTranslate(node.translated_name ?? node.name),
			selectable: node.is_visible,
			children: normalise(node.children ?? [])
		}));
	}

	onMount(() => {
		if (hidden) return;
		isLoading = true;
		fetch(`/asset-class/tree${visibleOnly ? '?visible_only=true' : ''}`)
			.then((res) => (res.ok ? res.json() : []))
			.then((data) => {
				nodes = normalise(data ?? []);
			})
			.catch((e) => console.error('AssetClassTreeSelect: failed to fetch tree', e))
			.finally(() => (isLoading = false));
	});
</script>

<TreeSelect
	{form}
	{field}
	{nodes}
	{label}
	{helpText}
	{disabled}
	{hidden}
	{isLoading}
	{cacheLock}
	{onChange}
	{excludeSubtreeOf}
	fallbackLabel={fallbackLabel ? safeTranslate(fallbackLabel) : null}
	bind:cachedValue
	icon="fa-solid fa-sitemap"
/>
