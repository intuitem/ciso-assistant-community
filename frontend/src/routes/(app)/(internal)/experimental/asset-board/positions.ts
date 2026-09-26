import { browser } from '$app/environment';

export interface XY {
	x: number;
	y: number;
}

export interface Viewport {
	x: number;
	y: number;
	zoom: number;
}

const positionsKey = (folderId: string) => `assetBoard:positions:${folderId}`;
const viewportKey = (folderId: string) => `assetBoard:viewport:${folderId}`;

export function loadPositions(folderId: string): Record<string, XY> {
	if (!browser) return {};
	try {
		const raw = localStorage.getItem(positionsKey(folderId));
		if (!raw) return {};
		const parsed = JSON.parse(raw);
		return typeof parsed === 'object' && parsed !== null ? parsed : {};
	} catch {
		return {};
	}
}

export function savePositions(folderId: string, positions: Record<string, XY>): void {
	if (!browser) return;
	try {
		localStorage.setItem(positionsKey(folderId), JSON.stringify(positions));
	} catch {
		// ignore quota errors
	}
}

export function loadViewport(folderId: string): Viewport | null {
	if (!browser) return null;
	try {
		const raw = localStorage.getItem(viewportKey(folderId));
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		if (
			parsed &&
			typeof parsed.x === 'number' &&
			typeof parsed.y === 'number' &&
			typeof parsed.zoom === 'number'
		) {
			return parsed as Viewport;
		}
		return null;
	} catch {
		return null;
	}
}

export function saveViewport(folderId: string, viewport: Viewport): void {
	if (!browser) return;
	try {
		localStorage.setItem(viewportKey(folderId), JSON.stringify(viewport));
	} catch {
		// ignore quota errors
	}
}

const pinnedKey = (folderId: string) => `assetBoard:pinned:${folderId}`;

export function loadPinned(folderId: string): string[] {
	if (!browser) return [];
	try {
		const parsed = JSON.parse(localStorage.getItem(pinnedKey(folderId)) ?? '[]');
		return Array.isArray(parsed) ? parsed.filter((v) => typeof v === 'string') : [];
	} catch {
		return [];
	}
}

export function savePinned(folderId: string, ids: string[]): void {
	if (!browser) return;
	try {
		localStorage.setItem(pinnedKey(folderId), JSON.stringify(ids));
	} catch {
		// ignore quota errors
	}
}
