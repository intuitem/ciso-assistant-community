export function formatStringToDate(inputString: string) {
	const date = new Date(inputString);
	return date.toLocaleDateString('en-US', {
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
