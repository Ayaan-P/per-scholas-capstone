import Link from 'next/link'
import { getAllPosts } from '../../utils/blog'

export const metadata = {
  title: 'Blog | FundFish',
  description: 'Technical insights and updates from the FundFish team. Learn about AI-powered grant discovery, nonprofit tech, and building in public.',
  openGraph: {
    title: 'Blog | FundFish',
    description: 'Technical insights and updates from the FundFish team.',
    type: 'website',
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
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-4">
            Dev Blog
          </h1>
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
