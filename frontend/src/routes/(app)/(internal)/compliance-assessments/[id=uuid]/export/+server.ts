import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Remove unsafe characters and normalize the filename (but keep Unicode letters)
function sanitizeFileName(name: string): string {
	return name
		.normalize('NFKC') // Normalize Unicode
		.replace(/[\x00-\x1F<>:”/\\|?*\u007F;’`\u2018\u2019\u201C\u201D()\[\]{}]/g, ‘-’) // Remove dangerous characters
		.replace(/\s+/g, '-') // Replace whitespace with dash
		.replace(/\.+$/g, '') // Remove trailing dots
		.replace(/^-+|-+$/g, '') // Trim leading/trailing dashes
		.replace(/-+/g, '-') // Collapse multiple dashes
		.substring(0, 100); // Truncate to avoid overly long names
}

// Format date as YYYY-MM-DD_HH-MM-SS (safe and readable)
function formatDateForFilename(date: Date = new Date()): string {
	const pad = (n: number) => n.toString().padStart(2, '0');
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}_${pad(date.getHours())}-${pad(date.getMinutes())}-${pad(date.getSeconds())}`;
}

export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/export/`;

	// Fetch the compliance assessment details
	const compliance_assessment = await fetch(`${BASE_API_URL}/${URLModel}/${params.id}/`).then(
		(res) => res.json()
	);

	// Build and sanitize the filename
	const namePart = `${compliance_assessment.name}-${compliance_assessment.framework.str}`;
	const datePart = formatDateForFilename(); // e.g. 2025-06-26_16-45-12
	const sanitizedName = sanitizeFileName(namePart);
	const finalFileName = `${sanitizedName}-${datePart}.zip`;
	const urlEncodedFileName = encodeURIComponent(finalFileName);

	// Fetch the ZIP blob
	const blobData = await fetch(endpoint).then((res) => {
		if (!res.ok) {
			throw error(400, 'Error fetching the ZIP file');
		}
		return res.blob();
	});

	// ASCII-safe fallback: strip anything outside printable ASCII
	const asciiFileName = finalFileName
		.replace(/[^\x20-\x7E]/g, '-') // strip non-printable / non-ASCII
		.replace(/[;"%\\]/g, '-') // strip header-delimiter and quoting chars
		.replace(/-+/g, '-'); // collapse consecutive dashes

	// Return the file with proper headers
	return new Response(blobData, {
		headers: {
			'Content-Type': 'application/zip',
			'Content-Disposition': `attachment; filename="${asciiFileName}"; filename*=utf-8''${urlEncodedFileName}`
		}
	});
};
