export function formatStringToDate(inputString: string, locale = 'en') {
	const date = new Date(inputString);
	return date.toLocaleDateString(locale, {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	});
}

export const isURL = (url: string) => {
	try {
		const urlToCheck = new URL(url);
		if (urlToCheck.protocol !== 'http:' && urlToCheck.protocol !== 'https:') return false;
		return true;
	} catch (e) {
		return false;
	}
};

export function getRequirementTitle(ref_id: string, name: string) {
	const pattern = (ref_id ? 2 : 0) + (name ? 1 : 0);
	const title: string =
		pattern == 3 ? `${ref_id} - ${name}` : pattern == 2 ? ref_id : pattern == 1 ? name : '';
	return title;
}

export function displayScoreColor(value: number | null, max_score: number, inversedColors = false) {
	value ??= 0;
	value = (value * 100) / max_score;
	if (inversedColors) {
		if (value < 25) {
			return 'stroke-green-300';
		}
		if (value < 50) {
			return 'stroke-yellow-300';
		}
		if (value < 75) {
			return 'stroke-orange-400';
		}
		return 'stroke-red-400';
	} else {
		if (value < 25) {
			return 'stroke-red-400';
		}
		if (value < 50) {
			return 'stroke-orange-400';
		}
		if (value < 75) {
			return 'stroke-yellow-300';
		}
		return 'stroke-green-300';
	}
}

export function formatScoreValue(value: number, max_score: number, fullDonut = false) {
	if (value === null) {
		return 0;
	} else if (fullDonut) {
		return 100;
	}
	return (value * 100) / max_score;
}

export function getSecureRedirect(url: any): string {
	const SECURE_REDIRECT_URL_REGEX = /^\/\w+/;
	return typeof url === 'string' && SECURE_REDIRECT_URL_REGEX.test(url) ? url : '';
}

export function darkenColor(hex: string, amount: number) {
	hex = hex.slice(1);
	const num = parseInt(hex, 16);

	let r = (num >> 16) - amount * 255;
	let g = ((num >> 8) & 0x00ff) - amount * 255;
	let b = (num & 0x0000ff) - amount * 255;

	r = Math.max(0, Math.min(255, r));
	g = Math.max(0, Math.min(255, g));
	b = Math.max(0, Math.min(255, b));

	return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

export function stringify(value: string | number | boolean | null = null) {
	return String(value)
		.toLowerCase()
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '');
}

export function isDark(hexcolor: string): boolean {
	const r = parseInt(hexcolor.slice(1, 3), 16);
	const g = parseInt(hexcolor.slice(3, 5), 16);
	const b = parseInt(hexcolor.slice(5, 7), 16);
	// compute brightness from rgb values
	// https://www.w3.org/tr/aert/#color-contrast
	const brightness = (r * 299 + g * 587 + b * 114) / 1000;
	return brightness < 128;
}

// Get the search key from an option object or the option itself
// if it's a string or number
export const getSearchTarget = (opt: Option): string => {
	// Handle primitive values (string/number)
	if (typeof opt === 'string' || typeof opt === 'number') {
		return String(opt).trim();
	}

	// Handle non-object types
	if (!opt || typeof opt !== 'object') {
		return '';
	}

	// Validate object structure
	if (opt.label === undefined) {
		const opt_str = JSON.stringify(opt);
		console.error(`MultiSelect option ${opt_str} is an object but has no label key`);
		return '';
	}

	// Build searchable components
	const components: string[] = [];

	// Add path information (hierarchical context)
	if (opt.path && Array.isArray(opt.path)) {
		const pathString = opt.path
			.filter(Boolean) // Remove empty/null values
			.map((item) => String(item).trim())
			.join(' ');
		if (pathString) {
			components.push(pathString);
		}
	}

	// Add main label (primary searchable content)
	const mainLabel = String(opt.label || '').trim();
	if (mainLabel) {
		components.push(mainLabel);
	}

	// Add translated label if different from main label
	if (opt.translatedLabel && opt.translatedLabel !== opt.label) {
		const translatedLabel = String(opt.translatedLabel).trim();
		if (translatedLabel && translatedLabel !== mainLabel) {
			components.push(translatedLabel);
		}
	}

	// Add value if it's different from label (for ID-based searches)
	if (opt.value !== undefined && opt.value !== opt.label) {
		const valueString = String(opt.value).trim();
		if (valueString && valueString !== mainLabel) {
			components.push(valueString);
		}
	}

	// Add info string content
	if (opt.infoString?.string) {
		const infoString = String(opt.infoString.string).trim();
		if (infoString) {
			components.push(infoString);
		}
	}

	// Combine all components with spaces
	const searchTarget = components.join(' ');

	// Normalize the search target
	return normalizeSearchString(searchTarget);
};

// Helper function to normalize search strings for better matching
export function normalizeSearchString(str: string): string {
	return str
		.toLowerCase()
		.normalize('NFD') // Decompose accented characters
		.replace(/\p{Diacritic}/gu, '') // Remove combining marks (diacritics)
		.replace(/[^\w\s-]/g, ' ') // Replace special chars with spaces
		.replace(/\s+/g, ' ') // Collapse multiple spaces
		.trim();
}
