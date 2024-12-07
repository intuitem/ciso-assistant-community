
import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
  const URLModel = 'compliance-assessments';
  const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/word_report/`;

  const res = await fetch(endpoint);
  if (!res.ok) {
    error(400, 'Error fetching the Word file');
  }

  const fileName = `audit-report-${new Date().toISOString()}.docx`;

  return new Response(await res.blob(), {
    headers: {
      'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'Content-Disposition': `attachment; filename="${fileName}"`
    }
  });
};
