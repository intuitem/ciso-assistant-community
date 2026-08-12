import { z } from 'zod';

// Infrastructure configuration settings. Currently just the list of IPs/CIDRs
// allowed to reach the backend; the object can grow more keys over time.

function isIpv4(addr: string): boolean {
	const parts = addr.split('.');
	if (parts.length !== 4) return false;
	return parts.every((p) => {
		if (!/^\d{1,3}$/.test(p)) return false;
		if (p.length > 1 && p[0] === '0') return false; // no leading zeros (matches Python ipaddress)
		return Number(p) <= 255;
	});
}

function isIpv6(addr: string): boolean {
	if (!/^[0-9a-fA-F:]+$/.test(addr)) return false;

	const validGroup = (g: string) => /^[0-9a-fA-F]{1,4}$/.test(g);
	const parts = addr.split('::');
	if (parts.length > 2) return false; // at most one '::'

	if (parts.length === 1) {
		// No compression: must be exactly 8 valid hextets.
		const groups = addr.split(':');
		return groups.length === 8 && groups.every(validGroup);
	}

	// With '::': each side is a (possibly empty) run of valid hextets, and the
	// '::' stands for at least one zero group, so the two sides total <= 7.
	const head = parts[0] ? parts[0].split(':') : [];
	const tail = parts[1] ? parts[1].split(':') : [];
	if (!head.every(validGroup) || !tail.every(validGroup)) return false;
	return head.length + tail.length <= 7;
}

// Validate a single IP address or CIDR range. Kept close to the backend
// (Python `ipaddress`), but the backend remains the source of truth.
export function isIpOrCidr(value: string): boolean {
	const v = value.trim();
	if (!v) return false;

	const slash = v.indexOf('/');
	const addr = slash === -1 ? v : v.slice(0, slash);

	if (slash !== -1) {
		const prefix = v.slice(slash + 1);
		if (!/^\d{1,3}$/.test(prefix)) return false;
		const max = addr.includes(':') ? 128 : 32;
		const n = Number(prefix);
		if (n < 0 || n > max) return false;
	}

	return addr.includes(':') ? isIpv6(addr) : isIpv4(addr);
}

// Normalise for case-insensitive duplicate comparison (IPv6 is hex, so
// 2001:DB8::1 and 2001:db8::1 are the same address). The backend canonicalises
// fully on save; this just prevents obvious client-side dupes.
export const normalizeIpForCompare = (value: string) => value.trim().toLowerCase();

// Max length of a textual IPv6 + prefix (e.g. full address + "/128").
export const IP_INPUT_MAXLENGTH = 49;

// Hard limit on the number of allowed IPs (kept in sync with the backend).
export const MAX_ALLOWED_IPS = 50;

export const InfraConfigSchema = z.object({
	allowed_ips: z.array(z.string()).default([])
});
