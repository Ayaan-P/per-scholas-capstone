import { getAllPosts } from '@/utils/blog';
import { NextResponse } from 'next/server';

export async function GET() {
  const posts = getAllPosts().slice(0, 10);

  const postList = posts
    .map(
      (p) =>
        `- [${p.title}](https://fundfish.pro/blog/${p.slug}): ${p.description || ''}`
    )
    .join('\n');

  const content = `# FundFish

> FundFish is an AI fundraising platform for nonprofits. It matches organizations with relevant grants and automates proposal writing.

## What is FundFish?

FundFish helps nonprofits find and win grants. AI analyzes each organization's mission, programs, and history to match them with grants they're most likely to win. Then it helps write proposals.

## Key Features
- AI grant matching
- Grant database search
- Proposal assistance
- Organization profile management
- Grant deadline tracking

## For Nonprofits
- App: https://fundfish.pro
- Blog: https://fundfish.pro/blog

## Blog Articles

${postList}
`;

  return new NextResponse(content, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
