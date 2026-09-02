import { browser } from '$app/environment';

export function isDarkTheme(): boolean {
	return browser && document.documentElement.classList.contains('dark');
}

interface ThemeAwareChartOptions {
	rendererOpts?: Record<string, any>;
	/** Called after every (re)init so the component can attach instance-level
	 *  listeners (e.g. chart.on('click', …)) that don't survive a dispose. */
	onChart?: (chart: any) => void;
	/** Set false when the caller installs its own resize handling (e.g. a debounced
	 *  one for an expensive layout) and does not want the built-in listener too. */
	manageResize?: boolean;
}

/**
 * Inits an ECharts instance that rebuilds itself whenever the `dark` class on
 * <html> flips. `buildOption` is re-invoked on each theme change, so inline
 * theme-conditional colors are recomputed instead of frozen at first paint.
 * Returns a dispose function.
 */
export function mountThemeAwareChart(
	echarts: any,
	container: HTMLElement,
	buildOption: () => any,
	{ rendererOpts = { renderer: 'svg' }, onChart, manageResize = true }: ThemeAwareChartOptions = {}
): () => void {
	let dark = isDarkTheme();
	let chart: any;
	let firstPaint = true;

	const init = () => {
		chart = echarts.init(container, dark ? 'dark' : null, rendererOpts);
		const option = { ...buildOption(), backgroundColor: 'transparent' };
		// A theme-flip re-init must snap straight to the final frame: animating it looks
		// janky live, and window.print() can capture the chart mid-animation (blank/partial
		// in PDF exports). Only the very first mount keeps its entry animation.
		if (!firstPaint) option.animation = false;
		chart.setOption(option, true);
		onChart?.(chart);
		firstPaint = false;
	};
	init();
	container.setAttribute('data-theme-managed', 'true');

	const resize = () => chart.resize();
	if (manageResize) window.addEventListener('resize', resize);

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
		if (manageResize) window.removeEventListener('resize', resize);
		container.removeAttribute('data-theme-managed');
		chart.dispose();
	};
}
