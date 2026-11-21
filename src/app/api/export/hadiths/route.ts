/** Curator-only streaming CSV export of live hadiths (section 10.1). Gated by src/proxy.ts and requireCurator(). */
import { NextResponse, type NextRequest } from 'next/server';
import { z } from 'zod';
import { EXPORT_EDGE_KEYS, EXPORT_FIELD_KEYS, exportColumns, exportHadithBatches } from '@/db/queries/hadith-export-review';
import { requireCurator, UnauthorizedError } from '@/lib/auth/require-curator';
import { authEnabled } from '@/lib/auth/switches';

export const dynamic = 'force-dynamic';

const commaList = (allowed: string[]) =>
  z
    .string()
    .default('')
    .transform((value) => value.split(',').map((item) => item.trim()).filter(Boolean))
    .pipe(z.array(z.enum(allowed as [string, ...string[]])).max(allowed.length));

const exportQuery = z.object({
  fields: commaList(EXPORT_FIELD_KEYS).pipe(z.array(z.string()).min(1)),
  edges: commaList(EXPORT_EDGE_KEYS),
  tradition: z.string().trim().max(50).optional(),
  source: z.string().trim().max(200).optional(),
});

/** One RFC 4180 cell; a leading = + @ would run as a spreadsheet formula, so it is neutralised with a quote. */
function csvCell(value: string): string {
  const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return `"${safe.replace(/"/g, '""')}"`;
}

const csvLines = (rows: Record<string, string>[], columns: string[]) =>
  rows.map((row) => columns.map((column) => csvCell(row[column] ?? '')).join(',') + '\r\n').join('');

export async function GET(request: NextRequest) {
  if (!authEnabled()) return new NextResponse('Not found', { status: 404 });
  try {
    await requireCurator();
  } catch (error) {
    if (error instanceof UnauthorizedError) return new NextResponse(error.message, { status: 401 });
    throw error;
  }
  const params = exportQuery.safeParse(Object.fromEntries(request.nextUrl.searchParams.entries()));
  if (!params.success) return new NextResponse('Invalid export request.', { status: 400 });

  const batches = exportHadithBatches(params.data);
  const first = await batches.next();
  if (first.done) return new NextResponse(null, { status: 204 });

  const columns = exportColumns(params.data);
  const encoder = new TextEncoder();
  const header = '﻿' + columns.map(csvCell).join(',') + '\r\n';
  let sentFirst = false;
  const body = new ReadableStream<Uint8Array>({
    async pull(controller) {
      if (!sentFirst) {
        sentFirst = true;
        controller.enqueue(encoder.encode(header + csvLines(first.value, columns)));
        return;
      }
      const next = await batches.next();
      if (next.done) return controller.close();
      controller.enqueue(encoder.encode(csvLines(next.value, columns)));
    },
    async cancel() {
      await batches.return(undefined);
    },
  });
  return new NextResponse(body, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="hadith-export-${new Date().toISOString().slice(0, 10)}.csv"`,
      'Cache-Control': 'no-store',
    },
  });
}
