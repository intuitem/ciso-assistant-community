export interface TocItem {
	id: string;
	title: string;
	level: number;
}

export function generateTocFromElements(selector: string = '[data-toc]'): TocItem[] {
	if (typeof document === 'undefined') return [];

	const elements = document.querySelectorAll(selector);
	const items: TocItem[] = [];

	elements.forEach((element, index) => {
		const title =
			element.getAttribute('data-toc-title') ||
			element.textContent?.trim() ||
			`Section ${index + 1}`;

		let id = element.id;
		if (!id) {
			id = `toc-section-${index}`;
			element.id = id;
		}

		const level = parseInt(element.getAttribute('data-toc-level') || '0');

		items.push({ id, title, level });
	});

	return items;
}

export function truncateTitle(title: string, maxLength: number = 40): string {
	return title.length > maxLength ? title.substring(0, maxLength) + '...' : title;
}
