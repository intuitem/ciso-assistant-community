export const complianceResultColorMap = {
	not_assessed: '#d1d5db',
	partially_compliant: '#fde047',
	non_compliant: '#f87171',
	not_applicable: '#000000',
	compliant: '#86efac'
};

export const complianceStatusColorMap = {
	to_do: '#9ca3af',
	in_progress: '#f59e0b',
	in_review: '#3b82f6',
	done: '#86efac'
};

export function darkenColor(hex: string, amount: number) {
	hex = hex.slice(1);
	let num = parseInt(hex, 16);

	let r = (num >> 16) - amount * 255;
	let g = ((num >> 8) & 0x00ff) - amount * 255;
	let b = (num & 0x0000ff) - amount * 255;

	r = Math.max(0, Math.min(255, r));
	g = Math.max(0, Math.min(255, g));
	b = Math.max(0, Math.min(255, b));

	return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}
