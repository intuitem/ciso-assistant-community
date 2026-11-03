// Shared by every place a metric value is shown: the decimals it is rounded
// to, its direction, and the calendar period an entered value answers for.

export type Direction = 'higher' | 'lower' | 'none';

// Decimals shown for a definition that sets none, by unit name. Mirrors
// metrology.models.UNIT_DEFAULT_DECIMALS.
const UNIT_DEFAULT_DECIMALS: Record<string, number> = { percentage: 1, count: 0 };

export function displayDecimals(definition: any): number | null {
	if (definition?.decimals !== null && definition?.decimals !== undefined) {
		return Number(definition.decimals);
	}
	const unit = definition?.unit?.name;
	return unit && unit in UNIT_DEFAULT_DECIMALS ? UNIT_DEFAULT_DECIMALS[unit] : null;
}

/** A number rounded half up to the definition's decimals, as text; anything
 * that is not a finite number comes back as is. */
export function formatMetricNumber(value: unknown, definition: any): string {
	const n = typeof value === 'number' ? value : Number(value);
	if (value === null || value === undefined || value === '' || !Number.isFinite(n)) {
		return String(value ?? '');
	}
	const decimals = displayDecimals(definition);
	if (decimals === null) return String(n);
	// toFixed rounds binary floats (1.005 -> 1.00); nudge with a tiny epsilon
	// in the value's own direction so .5 cases round half up as the backend does.
	const factor = 10 ** decimals;
	const rounded = Math.round((Math.abs(n) + Number.EPSILON) * factor) / factor;
	return (n < 0 ? -rounded : rounded).toFixed(decimals);
}

export function directionOf(definition: any): Direction {
	const value = definition?.higher_is_better;
	if (value === null || value === undefined) return 'none';
	return value ? 'higher' : 'lower';
}

export function higherIsBetterFor(direction: Direction): boolean | null {
	return direction === 'none' ? null : direction === 'higher';
}

// ---------- calendar periods (mirrors metrology.series.period_start, in UTC) ----------

export function periodStart(moment: Date, frequency: string | null | undefined): Date {
	const d = new Date(moment);
	if (frequency === '15min') {
		d.setUTCMinutes(d.getUTCMinutes() - (d.getUTCMinutes() % 15), 0, 0);
		return d;
	}
	if (frequency === 'hourly') {
		d.setUTCMinutes(0, 0, 0);
		return d;
	}
	d.setUTCHours(0, 0, 0, 0);
	if (frequency === 'weekly') {
		const weekday = (d.getUTCDay() + 6) % 7; // Monday = 0
		d.setUTCDate(d.getUTCDate() - weekday);
		return d;
	}
	if (frequency === 'monthly') {
		d.setUTCDate(1);
		return d;
	}
	if (frequency === 'quarterly') {
		d.setUTCMonth(Math.floor(d.getUTCMonth() / 3) * 3, 1);
		return d;
	}
	if (frequency === 'yearly') {
		d.setUTCMonth(0, 1);
		return d;
	}
	return d;
}

/** How the period starting at `start` reads: "October 2026", "Q4 2026",
 * "2026", "Week of 2 Nov 2026", or the day. */
export function periodLabel(
	start: Date,
	frequency: string | null | undefined,
	locale?: string
): string {
	if (frequency === 'monthly') {
		return start.toLocaleDateString(locale, { month: 'long', year: 'numeric', timeZone: 'UTC' });
	}
	if (frequency === 'quarterly') {
		return `Q${Math.floor(start.getUTCMonth() / 3) + 1} ${start.getUTCFullYear()}`;
	}
	if (frequency === 'yearly') return String(start.getUTCFullYear());
	const day = start.toLocaleDateString(locale, {
		day: 'numeric',
		month: 'short',
		year: 'numeric',
		timeZone: 'UTC'
	});
	if (frequency === 'weekly') return `${day} →`;
	if (frequency === '15min' || frequency === 'hourly') {
		return start.toLocaleString(locale, { timeZone: 'UTC' });
	}
	return day;
}

/** Whether entered values of this frequency answer for a period at all:
 * sub-daily collection is automated and keeps timestamps only. */
export function hasPeriods(frequency: string | null | undefined): boolean {
	return !!frequency && frequency !== '15min' && frequency !== 'hourly';
}
