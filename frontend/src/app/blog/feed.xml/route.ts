import { getAllPosts } from '../../../utils/blog'

const SITE_URL = 'https://fundfish.pro'

export async function GET() {
  const posts = getAllPosts()

  const rssItems = posts
    .map((post) => {
      const pubDate = post.date ? new Date(post.date).toUTCString() : new Date().toUTCString()
      const link = `${SITE_URL}/blog/${post.slug}`
      
      return `
    <item>
      <title><![CDATA[${post.title}]]></title>
      <link>${link}</link>
      <guid isPermaLink="true">${link}</guid>
      <pubDate>${pubDate}</pubDate>
      <description><![CDATA[${post.description || ''}]]></description>
      ${post.tags.map((tag) => `<category>${tag}</category>`).join('\n      ')}
    </item>`
    })
    .join('')

  const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>FundFish Dev Blog</title>
    <link>${SITE_URL}/blog</link>
    <description>Technical insights and updates from the FundFish team. Learn about AI-powered grant discovery, nonprofit tech, and building in public.</description>
    <language>en-us</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${SITE_URL}/blog/feed.xml" rel="self" type="application/rss+xml"/>
    <image>
      <url>${SITE_URL}/favicon.ico</url>
      <title>FundFish Dev Blog</title>
      <link>${SITE_URL}/blog</link>
    </image>
    ${rssItems}
  </channel>
</rss>`

  return new Response(rss, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=3600, s-maxage=3600',
    },
  })
}
