import { readable } from 'svelte/store';
import { page as pageState } from './app-state';

export const page = readable(pageState);
export const navigating = readable(null);
export const updated = readable(false);
export const getStores = () => ({ page, navigating, updated });
