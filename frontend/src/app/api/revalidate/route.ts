import { revalidatePath } from 'next/cache';
import { NextRequest, NextResponse } from 'next/server';

const SECRET = process.env.REVALIDATE_SECRET || 'fundfish-revalidate-2026';

export async function POST(request: NextRequest) {
  const { slug, secret } = await request.json();
  if (secret !== SECRET)
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  if (slug) revalidatePath(`/blog/${slug}`);
  revalidatePath('/blog');
  revalidatePath('/sitemap.xml');

  return NextResponse.json({ revalidated: true });
}
