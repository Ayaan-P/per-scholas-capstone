import Link from 'next/link'
import { getAllPosts } from '../../utils/blog'

export const revalidate = 3600;

export const metadata = {
  title: 'Blog | FundFish',
  description: 'Technical insights and updates from the FundFish team. Learn about AI-powered grant discovery, nonprofit tech, and building in public.',
  openGraph: {
    title: 'Blog | FundFish',
    description: 'Technical insights and updates from the FundFish team.',
    type: 'website',
    url: 'https://fundfish.pro/blog',
    images: [{ url: 'https://fundfish.pro/opengraph-image', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Blog | FundFish',
    description: 'Technical insights and updates from the FundFish team.',
    images: ['https://fundfish.pro/twitter-image'],
  },
}

function formatDate(dateString: string): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export default function BlogPage() {
  const posts = getAllPosts()

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-12 sm:py-16">
        {/* Header */}
        <div className="mb-12">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-900">
              Dev Blog
            </h1>
            <Link
              href="/blog/feed.xml"
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-orange-600 bg-orange-50 rounded-lg hover:bg-orange-100 transition-colors"
              title="Subscribe to RSS feed"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="6.18" cy="17.82" r="2.18"/>
                <path d="M4 4.44v2.83c7.03 0 12.73 5.7 12.73 12.73h2.83c0-8.59-6.97-15.56-15.56-15.56zm0 5.66v2.83c3.9 0 7.07 3.17 7.07 7.07h2.83c0-5.47-4.43-9.9-9.9-9.9z"/>
              </svg>
              RSS
            </Link>
          </div>
          <p className="text-xl text-gray-600">
            Building AI-powered fundraising for nonprofits. Technical insights, learnings, and updates.
          </p>
        </div>

        {/* Posts List */}
        {posts.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">No posts yet. Check back soon!</p>
          </div>
        ) : (
          <div className="space-y-8">
            {posts.map((post) => (
              <article
                key={post.slug}
                className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8 hover:shadow-md transition-shadow duration-200"
              >
                <Link href={`/blog/${post.slug}`} className="block group">
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-3">
                    <h2 className="text-2xl font-bold text-gray-900 group-hover:text-perscholas-primary transition-colors">
                      {post.title}
                    </h2>
                    {post.date && (
                      <time className="text-sm text-gray-500 whitespace-nowrap">
                        {formatDate(post.date)}
                      </time>
                    )}
                  </div>
                  {post.description && (
                    <p className="text-gray-600 mb-4 line-clamp-2">
                      {post.description}
                    </p>
                  )}
                  {post.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {post.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-3 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </Link>
              </article>
            ))}
          </div>
        )}

        {/* Subscribe CTA */}
        <div className="mt-16 bg-gradient-to-r from-perscholas-primary to-blue-600 rounded-2xl p-8 text-center text-white">
          <h3 className="text-2xl font-bold mb-2">Stay Updated</h3>
          <p className="text-blue-100 mb-4">
            Follow our journey building AI-powered fundraising tools.
          </p>
          <Link
            href="/signup"
            className="inline-block px-6 py-3 bg-white text-perscholas-primary font-semibold rounded-xl hover:bg-blue-50 transition-colors"
          >
            Get Started Free
          </Link>
        </div>
      </div>
    </div>
  )
}
