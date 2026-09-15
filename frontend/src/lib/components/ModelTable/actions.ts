// Shared Data/Table Actions

// Data Table (only) ---

/** Svelte Action for applying sort asc/dsc classes. */
export function tableInteraction(node: HTMLElement) {
	const classAsc = 'table-sort-asc';
	const classDsc = 'table-sort-dsc';
	// Click Handler
	const onClick = (e: Event) => {
		if (!(e.target instanceof Element)) return;
		const sortTarget = e.target;
		// Get target state before modification
		const targetAscSorted = sortTarget.classList.contains(classAsc);
		const sortTargetKey = sortTarget.getAttribute('data-sort');
		// Clear asc class
		const elemAsc = node.querySelector(`.${classAsc}`);
		if (elemAsc) elemAsc.classList.remove(classAsc);
		// Clear dsc class
		const elemDsc = node.querySelector(`.${classDsc}`);
		if (elemDsc) elemDsc.classList.remove(classDsc);
		// Set new sort class
		if (sortTargetKey) {
			const classToApply = targetAscSorted ? classDsc : classAsc;
			e.target.classList.add(classToApply);
		}
	};
	// Events
	node.addEventListener('click', onClick);
	// Lifecycle
	return {
		destroy() {
			node.removeEventListener('click', onClick);
		}
	};
}
