import { browser } from '$app/environment';

export function isDarkTheme(): boolean {
	return browser && document.documentElement.classList.contains('dark');
}

interface ThemeAwareChartOptions {
	rendererOpts?: Record<string, any>;
	/** Called after every (re)init so the component can attach instance-level
	 *  listeners (e.g. chart.on('click', …)) that don't survive a dispose. */
	onChart?: (chart: any) => void;
}

/**
 * Inits an ECharts instance that rebuilds itself whenever the `dark` class on
 * <html> flips. `buildOption` is re-invoked on each theme change, so inline
 * theme-conditional colors are recomputed instead of frozen at first paint.
 * Returns a dispose function; the container is tagged `data-theme-managed` so
 * the global refreshECharts() in theme.ts skips it (no double dispose).
 */
export function mountThemeAwareChart(
	echarts: any,
	container: HTMLElement,
	buildOption: () => any,
	{ rendererOpts = { renderer: 'svg' }, onChart }: ThemeAwareChartOptions = {}
): () => void {
	let dark = isDarkTheme();
	let chart: any;

	const init = () => {
		chart = echarts.init(container, dark ? 'dark' : null, rendererOpts);
		chart.setOption({ ...buildOption(), backgroundColor: 'transparent' }, true);
		onChart?.(chart);
	};
	init();
	container.setAttribute('data-theme-managed', 'true');

	const resize = () => chart.resize();
	window.addEventListener('resize', resize);

	const observer = new MutationObserver(() => {
		const now = isDarkTheme();
		if (now === dark) return;
		dark = now;
		chart.dispose();
		init();
	});
	observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

	return () => {
		observer.disconnect();
		window.removeEventListener('resize', resize);
		container.removeAttribute('data-theme-managed');
		chart.dispose();
	};
}
