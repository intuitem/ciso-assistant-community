import { browser } from '$app/environment';

export interface EChartsThemeColors {
	textPrimary: string;
	textSecondary: string;
	background: string;
	gridLine: string;
	tooltipBg: string;
	tooltipBorder: string;
	tooltipText: string;
}

function getCssVar(name: string): string {
	if (!browser) return '';
	return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function getEChartsThemeColors(): EChartsThemeColors {
	if (!browser) {
		return {
			textPrimary: '#333333',
			textSecondary: '#666666',
			background: '#ffffff',
			gridLine: '#e0e0e0',
			tooltipBg: 'rgba(255, 255, 255, 0.95)',
			tooltipBorder: '#e0e0e0',
			tooltipText: '#333333'
		};
	}

	const isDark = document.documentElement.classList.contains('dark');

	return {
		textPrimary: getCssVar(isDark ? '--color-surface-50' : '--color-surface-950'),
		textSecondary: getCssVar(isDark ? '--color-surface-400' : '--color-surface-600'),
		background: getCssVar(isDark ? '--color-surface-950' : '--color-surface-50'),
		gridLine: getCssVar(isDark ? '--color-surface-700' : '--color-surface-200'),
		tooltipBg: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
		tooltipBorder: getCssVar(isDark ? '--color-surface-700' : '--color-surface-200'),
		tooltipText: getCssVar(isDark ? '--color-surface-50' : '--color-surface-950')
	};
}
