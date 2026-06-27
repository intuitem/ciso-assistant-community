import { browser } from '$app/environment';
import type { ModalStore, ModalSettings } from '$lib/components/Modals/stores';
import ExternalLinkConfirmModal from '$lib/components/Modals/ExternalLinkConfirmModal.svelte';

let globalModalStore: ModalStore | null = null;
let showWarningExternalLinks: boolean = true; // Default to true for safety

export const setGlobalModalStore = (modalStore: ModalStore) => {
	globalModalStore = modalStore;
};

export const setShowWarningExternalLinks = (enabled: boolean) => {
	showWarningExternalLinks = enabled;
};

// Guards author-supplied URLs against unsafe schemes (javascript:, data:, vbscript:, …)
// before they reach window.open/goto. Only absolute http(s) URLs are accepted.
export const isSafeExternalUrl = (url: string | undefined | null): boolean => {
	if (!url) return false;
	try {
		const parsed = new URL(url);
		return parsed.protocol === 'http:' || parsed.protocol === 'https:';
	} catch {
		return false;
	}
};

const isExternalLink = (url: string): boolean => {
	if (!browser) return false;
	try {
		return new URL(url, window.location.origin).origin !== window.location.origin;
	} catch {
		return false;
	}
};

const isInternalLink = (href: string): boolean => {
	return href.startsWith('/') || href.startsWith('#');
};

const showConfirmation = async (url: string): Promise<boolean> => {
	if (globalModalStore) {
		return new Promise((resolve) => {
			const modal: ModalSettings = {
				type: 'component',
				component: {
					ref: ExternalLinkConfirmModal,
					props: { url }
				},
				response: resolve
			};
			globalModalStore.trigger(modal);
		});
	}

	// Fallback to native confirm
	return confirm(
		`You are about to leave this site and go to:\n\n${url}\n\nDo you want to continue?`
	);
};

const handleLinkClick = async (anchor: HTMLAnchorElement, href: string, event: MouseEvent) => {
	if (isInternalLink(href) || !isExternalLink(href)) return;

	// If warning is disabled, allow the link to open normally
	if (!showWarningExternalLinks) {
		return;
	}

	event.preventDefault();
	const confirmed = await showConfirmation(href);
	if (confirmed) {
		const target = anchor.target || '_blank';
		window.open(href, target, 'noopener,noreferrer');
	}
};

export const interceptExternalLinks = () => {
	if (!browser) return;

	document.addEventListener('click', async (event) => {
		const anchor = (event.target as HTMLElement).closest('a[href]') as HTMLAnchorElement;
		if (!anchor) return;

		const href = anchor.getAttribute('href');
		if (!href) return;

		await handleLinkClick(anchor, href, event);
	});
};
