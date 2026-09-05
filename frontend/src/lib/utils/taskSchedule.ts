import { m } from '$paraglide/messages';

export interface TaskSchedule {
	frequency?: string;
	interval?: number;
}

/**
 * The recurrence rule in words: "Every 3 months" rather than MONTHLY/3.
 *
 * Built here rather than on the backend because Django's catalogue only carries
 * French, while the frontend catalogue covers every locale the product ships.
 * An interval of 1 gets its own wording ("Monthly", not "Every 1 months") since
 * that is how a cadence is actually said.
 */
export function scheduleLabel(schedule: TaskSchedule | null | undefined): string | null {
	const frequency = schedule?.frequency;
	if (!frequency) return null;

	const interval = Math.max(Math.trunc(Number(schedule?.interval ?? 1)) || 1, 1);

	const simple: Record<string, () => string> = {
		DAILY: m.scheduleDaily,
		WEEKLY: m.scheduleWeekly,
		MONTHLY: m.scheduleMonthly,
		YEARLY: m.scheduleYearly
	};
	const repeated: Record<string, (args: { count: number }) => string> = {
		DAILY: m.scheduleEveryNDays,
		WEEKLY: m.scheduleEveryNWeeks,
		MONTHLY: m.scheduleEveryNMonths,
		YEARLY: m.scheduleEveryNYears
	};

	if (interval === 1) return simple[frequency]?.() ?? null;
	return repeated[frequency]?.({ count: interval }) ?? null;
}
