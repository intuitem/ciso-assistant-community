import { persisted } from 'svelte-persisted-store';

export const licenseAboutToExpireToastShown = persisted('licence_about_to_expire_toast_shown', false, {
  storage: 'session'
});
