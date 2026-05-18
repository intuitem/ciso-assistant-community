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

export interface TrustZone {
	id: string;
	name: string;
	color: string;
	x: number;
	y: number;
	width: number;
	height: number;
}

const positionsKey = (folderId: string) => `assetBoard:positions:${folderId}`;
const viewportKey = (folderId: string) => `assetBoard:viewport:${folderId}`;
const zonesKey = (folderId: string) => `assetBoard:zones:${folderId}`;
const membershipKey = (folderId: string) => `assetBoard:membership:${folderId}`;

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

export function loadZones(folderId: string): TrustZone[] {
	if (!browser) return [];
	try {
		const raw = localStorage.getItem(zonesKey(folderId));
		if (!raw) return [];
		const parsed = JSON.parse(raw);
		if (!Array.isArray(parsed)) return [];
		return parsed.filter(
			(z) =>
				z &&
				typeof z.id === 'string' &&
				typeof z.name === 'string' &&
				typeof z.color === 'string' &&
				typeof z.x === 'number' &&
				typeof z.y === 'number' &&
				typeof z.width === 'number' &&
				typeof z.height === 'number'
		);
	} catch {
		return [];
	}
}

export function saveZones(folderId: string, zones: TrustZone[]): void {
	if (!browser) return;
	try {
		localStorage.setItem(zonesKey(folderId), JSON.stringify(zones));
	} catch {
		// ignore quota errors
	}
}

export function loadMembership(folderId: string): Record<string, string> {
	if (!browser) return {};
	try {
		const raw = localStorage.getItem(membershipKey(folderId));
		if (!raw) return {};
		const parsed = JSON.parse(raw);
		return typeof parsed === 'object' && parsed !== null ? parsed : {};
	} catch {
		return {};
	}
}

export function saveMembership(folderId: string, membership: Record<string, string>): void {
	if (!browser) return;
	try {
		localStorage.setItem(membershipKey(folderId), JSON.stringify(membership));
	} catch {
		// ignore quota errors
	}
}
