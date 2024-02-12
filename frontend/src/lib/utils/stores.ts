import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export const showNotification = writable(
	(browser && localStorage.getItem('showNotification')) || 'false'
);
showNotification.subscribe((val) => {
	if (browser) return (localStorage.showNotification = val);
});

export const breadcrumbObject = writable({ id: '', name: '', email: '' });
export const pageTitle = writable('');
