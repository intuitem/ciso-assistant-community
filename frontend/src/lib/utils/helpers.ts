export function formatStringToDate(inputString: string, locale: string = 'en') {
	const date = new Date(inputString);
	return date.toLocaleDateString(locale, {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	});
}

export const isURL = (url: string) => {
	try {
		new URL(url);
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

export function displayScoreColor(value: number, max_score: number) {
	value = (value * 100) / max_score;
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

export function formatScoreValue(value: number, max_score: number) {
	if (value === null) {
		return 0;
	}
	return (value * 100) / max_score;
}

export function getSecureRedirect(url: any): string {
	const SECURE_REDIRECT_URL_REGEX = /^\/(?!.*\/\/)[^\s]*$/;
	return typeof url === 'string' && SECURE_REDIRECT_URL_REGEX.test(url) ? url : '';
}
