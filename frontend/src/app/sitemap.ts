import { getAllPosts } from '@/utils/blog';

export default async function sitemap() {
  const posts = getAllPosts();

  const blogUrls = posts.map((post) => ({
    url: `https://fundfish.pro/blog/${post.slug}`,
    lastModified: new Date(post.date || Date.now()),
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }));

  return [
    {
      url: 'https://fundfish.pro',
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 1.0,
    },
    {
      url: 'https://fundfish.pro/blog',
      lastModified: new Date(),
      changeFrequency: 'daily' as const,
      priority: 0.9,
    },
    {
      url: 'https://fundfish.pro/opportunities',
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.8,
    },
    ...blogUrls,
  ];
}
