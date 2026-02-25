import Link from 'next/link'
import { getAllPosts, getAllTags } from '../../utils/blog'

export const revalidate = 3600

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
  const allTags = getAllTags()
  const [featured, ...rest] = posts

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-12 sm:py-16">
        {/* Header */}
        <div className="mb-12 flex items-end justify-between">
          <div>
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 tracking-tight">
              Blog
            </h1>
            <p className="mt-3 text-lg text-gray-500 max-w-lg">
              Building AI-powered fundraising for nonprofits. Technical insights, learnings, and updates.
            </p>
          </div>
          <Link
            href="/blog/feed.xml"
            className="hidden sm:flex items-center gap-2 px-4 py-2 text-sm font-medium text-orange-600 bg-orange-50 rounded-lg hover:bg-orange-100 transition-colors"
            title="Subscribe to RSS feed"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="6.18" cy="17.82" r="2.18"/>
              <path d="M4 4.44v2.83c7.03 0 12.73 5.7 12.73 12.73h2.83c0-8.59-6.97-15.56-15.56-15.56zm0 5.66v2.83c3.9 0 7.07 3.17 7.07 7.07h2.83c0-5.47-4.43-9.9-9.9-9.9z"/>
            </svg>
            RSS
          </Link>
        </div>

        {/* Tag Filter Pills */}
        {allTags.length > 1 && (
          <div className="flex flex-wrap gap-2 mb-10">
            {allTags.map((tag) => (
              <span
                key={tag}
                className="px-3.5 py-1.5 text-sm font-medium bg-white text-gray-600 rounded-full border border-gray-200 hover:border-[#006fb4]/30 hover:text-[#006fb4] transition-colors cursor-default"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {posts.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-400 text-lg">No posts yet. Check back soon!</p>
          </div>
        ) : (
          <>
            {/* Featured / Latest Post — Hero Card */}
            {featured && (
              <Link href={`/blog/${featured.slug}`} className="block group mb-12">
                <article className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#f0f7fc] via-white to-[#f0f7fc] border border-gray-100 p-8 sm:p-10 lg:p-12 hover:shadow-xl hover:border-[#006fb4]/10 transition-all duration-300">
                  <div className="absolute top-4 right-5 text-xs font-semibold uppercase tracking-wider text-[#006fb4]/40">
                    Latest
                  </div>
                  <div className="max-w-2xl">
                    <div className="flex flex-wrap items-center gap-3 text-sm text-gray-400 mb-4">
                      {featured.date && <time>{formatDate(featured.date)}</time>}
                      <span className="text-gray-300">·</span>
                      <span>{featured.readTime} min read</span>
                    </div>
                    <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 leading-tight group-hover:text-[#006fb4] transition-colors mb-4">
                      {featured.title}
                    </h2>
                    {featured.description && (
                      <p className="text-gray-500 text-lg leading-relaxed mb-5 line-clamp-3">
                        {featured.description}
                      </p>
                    )}
                    {featured.tags.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {featured.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-2.5 py-0.5 text-xs font-medium bg-[#006fb4]/8 text-[#006fb4] rounded-full"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </article>
              </Link>
            )}

            {/* Post Grid — 2 columns */}
            {rest.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {rest.map((post) => (
                  <Link key={post.slug} href={`/blog/${post.slug}`} className="block group">
                    <article className="h-full bg-white rounded-2xl border border-gray-100 p-6 sm:p-7 hover:shadow-lg hover:border-[#006fb4]/10 hover:-translate-y-0.5 transition-all duration-300">
                      <div className="flex items-center gap-3 text-sm text-gray-400 mb-3">
                        {post.date && <time>{formatDate(post.date)}</time>}
                        <span className="text-gray-300">·</span>
                        <span>{post.readTime} min read</span>
                      </div>
                      <h2 className="text-xl font-bold text-gray-900 leading-snug group-hover:text-[#006fb4] transition-colors mb-3">
                        {post.title}
                      </h2>
                      {post.description && (
                        <p className="text-gray-500 text-[15px] leading-relaxed line-clamp-2 mb-4">
                          {post.description}
                        </p>
                      )}
                      {post.tags.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-auto">
                          {post.tags.map((tag) => (
                            <span
                              key={tag}
                              className="px-2.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-500 rounded-full"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </article>
                  </Link>
                ))}
              </div>
            )}
          </>
        )}

        {/* Subscribe CTA — Premium */}
        <div className="mt-16">
          <div className="relative overflow-hidden bg-gradient-to-br from-[#006fb4] via-[#005a94] to-[#00476e] rounded-2xl p-10 sm:p-12 text-center text-white">
            <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")', backgroundSize: '128px 128px' }} />
            <div className="absolute -top-12 -right-12 w-48 h-48 bg-white/5 rounded-full" />
            <div className="absolute -bottom-8 -left-8 w-32 h-32 bg-white/5 rounded-full" />
            <div className="relative">
              <h3 className="text-2xl sm:text-3xl font-bold mb-3">Stay Updated</h3>
              <p className="text-blue-100/80 mb-6 text-lg max-w-md mx-auto">
                Follow our journey building AI-powered fundraising tools for nonprofits.
              </p>
              <Link
                href="/signup"
                className="inline-block px-8 py-3.5 bg-white text-[#006fb4] font-semibold rounded-xl hover:bg-blue-50 hover:shadow-lg transition-all duration-200 text-base"
              >
                Get Started Free
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
