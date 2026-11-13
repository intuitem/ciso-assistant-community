/**
 * Scroll each overflowing horizontal tab bar so its selected tab is visible,
 * e.g. after landing on `?tab=custom` on a narrow viewport. Only the bar scrolls, never the page.
 */
export function revealActiveTabs(root: ParentNode = document): void {
	const lists = root.querySelectorAll<HTMLElement>(
		"[data-scope='tabs'][data-part='list'][data-orientation='horizontal']"
	);
	for (const list of lists) {
		if (list.scrollWidth <= list.clientWidth) continue;
		const active = list.querySelector<HTMLElement>("[data-part='trigger'][data-selected]");
		if (!active) continue;
		const bar = list.getBoundingClientRect();
		const tab = active.getBoundingClientRect();
		// Margin clears the edge fade (2rem in app.css).
		const margin = 32;
		if (tab.left < bar.left) list.scrollLeft -= bar.left - tab.left + margin;
		else if (tab.right > bar.right) list.scrollLeft += tab.right - bar.right + margin;
	}
}
