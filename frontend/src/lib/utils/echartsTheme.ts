import { browser } from '$app/environment';

/**
 * Returns the ECharts theme name based on current dark mode state.
 */
export function getEChartsTheme(): string | null {
	if (!browser) return null;
	return document.documentElement.classList.contains('dark') ? 'dark' : null;
}

/**
 * Creates an ECharts instance with transparent background, automatic theme switching,
 * and resize handling. Returns a dispose function for cleanup.
 *
 * Usage in onMount:
 *   const echarts = await import('echarts');
 *   const { chart, dispose } = createThemeAwareChart(echarts, container, option, { renderer: 'svg' });
 *   return dispose;
 */
export function createThemeAwareChart(
	echarts: any,
	container: HTMLElement,
	option: any,
	rendererOpts?: Record<string, any>
): { chart: any; dispose: () => void } {
	option.backgroundColor = 'transparent';

	let chart = echarts.init(container, getEChartsTheme(), rendererOpts);
	chart.setOption(option);

	const resizeHandler = () => chart.resize();
	window.addEventListener('resize', resizeHandler);

	const observer = new MutationObserver(() => {
		const newTheme = getEChartsTheme();
		chart.dispose();
		chart = echarts.init(container, newTheme, rendererOpts);
		chart.setOption(option);
	});
	observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

	return {
		get chart() {
			return chart;
		},
		dispose() {
			observer.disconnect();
			window.removeEventListener('resize', resizeHandler);
			chart.dispose();
		}
	};
}
