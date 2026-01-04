<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	interface treeType {
		name: string;
		id: string;
		children: any[];
	}
	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		name?: string;
		tree: treeType[];
		translate?: boolean;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		name = '',
		tree,
		translate = false
	}: Props = $props();

	const translatedTree = $derived(
		tree.map((item) => ({
			...item,
			name: translate ? safeTranslate(item.name?.toLowerCase() || item.name) : item.name,
			children: item.children?.map((child) => ({
				...child,
				name: translate ? safeTranslate(child.name?.toLowerCase() || child.name) : child.name,
				children: child.children?.map((grandChild: any) => ({
					...grandChild,
					name: translate
						? safeTranslate(grandChild.name?.toLowerCase() || grandChild.name)
						: grandChild.name
				}))
			}))
		}))
	);

	const chart_id = `${name}_div`;
	let chart: any = null;
	let echarts: any = null;

	function createOption(data: any) {
		return {
			toolbox: {
				show: true,
				feature: {
					restore: { show: true }
				}
			},
			title: {
				subtext: title
			},
			tooltip: {
				trigger: 'item',
				formatter: '{b}/data: {c}'
			},
			series: {
				type: 'treemap',
				breadcrumb: {
					show: true,
					formatter: function (name: string, item: any) {
						if (item.value) {
							return name + ' (' + item.value + ')';
						}
						return name;
					},
					itemStyle: {
						color: '#f0f0f0',
						borderColor: '#d0d0d0',
						borderWidth: 1,
						shadowBlur: 3,
						shadowColor: 'rgba(0, 0, 0, 0.2)',
						textStyle: {
							color: '#333'
						}
					},
					emphasis: {
						itemStyle: {
							color: '#e0e0e0'
						}
					}
				},
				label: {
					show: true,
					formatter: function (params: any) {
						return params.name + '\n(' + params.value + ')';
					}
				},
				leafDepth: 1,
				roam: false,
				visibleMin: 1,
				colorSaturation: [0.3, 0.4],
				data: data,
				radius: [30, '95%'],
				sort: undefined,
				itemStyle: {
					borderRadius: 7,
					borderWidth: 2
				}
			}
		};
	}

	onMount(async () => {
		echarts = await import('echarts');
		chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		if (translatedTree?.length > 0) {
			chart.setOption(createOption(translatedTree));
		}

		window.addEventListener('resize', handleResize);
	});

	function handleResize() {
		if (chart) {
			chart.resize();
		}
	}

	// Update chart when tree data changes
	$effect(() => {
		if (chart && translatedTree?.length > 0) {
			chart.setOption(createOption(translatedTree));
		}
	});

	onDestroy(() => {
		if (typeof window !== 'undefined') {
			window.removeEventListener('resize', handleResize);
		}
		if (chart) {
			chart.dispose();
		}
	});
</script>

{#if tree.length === 0}
	<div class="flex flex-col justify-center items-center h-full">
		<span class="text-center text-gray-600">{m.noDataAvailable()}</span>
	</div>
{:else}
	<div id={chart_id} class="{width} {height} {classesContainer}"></div>
{/if}
