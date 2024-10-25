import { persisted } from 'svelte-persisted-store';

export const toastShown = persisted('toast_shown', false, {
  storage: 'session'
});
