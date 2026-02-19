import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export type ThemeMode = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'ciso-theme';

function getStoredTheme(): ThemeMode {
	if (!browser) return 'light';
	return (localStorage.getItem(STORAGE_KEY) as ThemeMode) || 'system';
}

function getSystemPreference(): 'light' | 'dark' {
	if (!browser) return 'light';
	return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function resolveTheme(mode: ThemeMode): 'light' | 'dark' {
	return mode === 'system' ? getSystemPreference() : mode;
}

async function refreshECharts(resolved: 'light' | 'dark') {
	try {
		const echarts = await import('echarts');
		// Find all ECharts containers and re-init with new theme
		document.querySelectorAll('[_echarts_instance_]').forEach((el) => {
			const instance = echarts.getInstanceByDom(el as HTMLElement);
			if (instance) {
				const option = instance.getOption();
				const rendererType = (instance as any)._zr?.painter?.type === 'canvas' ? 'canvas' : 'svg';
				instance.dispose();
				const newChart = echarts.init(
					el as HTMLElement,
					resolved === 'dark' ? 'dark' : null,
					{ renderer: rendererType }
				);
				option.backgroundColor = 'transparent';
				newChart.setOption(option);
			}
		});
	} catch {
		// ECharts not loaded yet, nothing to refresh
	}
}

function applyTheme(resolved: 'light' | 'dark') {
	if (!browser) return;
	const html = document.documentElement;
	if (resolved === 'dark') {
		html.classList.add('dark');
	} else {
		html.classList.remove('dark');
	}
	// Re-init all ECharts instances with the new theme
	refreshECharts(resolved);
}

export const themeMode = writable<ThemeMode>(getStoredTheme());
export const resolvedTheme = writable<'light' | 'dark'>(resolveTheme(getStoredTheme()));

themeMode.subscribe((mode) => {
	if (!browser) return;
	localStorage.setItem(STORAGE_KEY, mode);
	const resolved = resolveTheme(mode);
	resolvedTheme.set(resolved);
	applyTheme(resolved);
});

if (browser) {
	window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
		let currentMode: ThemeMode = 'system';
		themeMode.subscribe((m) => (currentMode = m))();
		if (currentMode === 'system') {
			const resolved = getSystemPreference();
			resolvedTheme.set(resolved);
			applyTheme(resolved);
		}
	});
}

export async function setTheme(mode: ThemeMode, syncToBackend = true) {
	themeMode.set(mode);
	if (syncToBackend && browser) {
		try {
			await fetch('/fe-api/user-preferences', {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ ui: { theme: mode } })
			});
		} catch (e) {
			console.warn('Failed to sync theme preference to server:', e);
		}
	}
}

export function initThemeFromUser(preferences: { ui?: { theme?: ThemeMode } } | undefined) {
	if (!browser) return;
	const serverTheme = preferences?.ui?.theme;
	if (serverTheme) {
		localStorage.setItem(STORAGE_KEY, serverTheme);
		themeMode.set(serverTheme);
	} else {
		themeMode.set(getStoredTheme());
	}
}
