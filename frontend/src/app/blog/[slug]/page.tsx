import { notFound } from 'next/navigation'
import Link from 'next/link'
import { getPostBySlug, getAllPostSlugs, extractHeadings } from '../../../utils/blog'
import { Metadata } from 'next'
import ReadingProgress from '../../components/ReadingProgress'
import ShareButtons from '../../components/ShareButtons'
import TableOfContents from '../../components/TableOfContents'
import MarkdownRenderer from '../../components/MarkdownRenderer'

export const dynamicParams = true
export const revalidate = 3600

interface BlogPostPageProps {
  params: {
    slug: string
  }
}

export async function generateStaticParams() {
  const slugs = getAllPostSlugs()
  return slugs.map((slug) => ({ slug }))
}

export async function generateMetadata({ params }: BlogPostPageProps): Promise<Metadata> {
  const post = getPostBySlug(params.slug)
  
  if (!post) {
    return { title: 'Post Not Found | FundFish Blog' }
  }

  return {
    title: `${post.title} | FundFish Blog`,
    description: post.description,
    openGraph: {
      title: post.title,
      description: post.description,
      type: 'article',
      publishedTime: post.date,
      tags: post.tags,
      url: `https://fundfish.pro/blog/${params.slug}`,
      images: [{ url: 'https://fundfish.pro/opengraph-image', width: 1200, height: 630 }],
    },
    twitter: {
      card: 'summary_large_image',
      title: post.title,
      description: post.description,
      images: ['https://fundfish.pro/twitter-image'],
    },
  }
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

export default function BlogPostPage({ params }: BlogPostPageProps) {
  const post = getPostBySlug(params.slug)

  if (!post) {
    notFound()
  }

  const headings = extractHeadings(post.content)
  const articleUrl = `https://fundfish.pro/blog/${params.slug}`

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    description: post.description,
    author: { '@type': 'Organization', name: 'FundFish' },
    publisher: {
      '@type': 'Organization',
      name: 'FundFish',
      url: 'https://fundfish.pro',
    },
    datePublished: post.date,
    keywords: post.tags?.join(', '),
  }

  return (
    <div className="min-h-screen bg-white">
      <ReadingProgress />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Hero Header */}
      <header className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-white via-[#f0f7fc] to-white" />
        <div className="relative max-w-3xl mx-auto px-4 pt-12 pb-10 sm:pt-16 sm:pb-14">
          {/* Back Link */}
          <Link
            href="/blog"
            className="inline-flex items-center text-sm text-gray-400 hover:text-[#006fb4] mb-8 transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Blog
          </Link>

          <h1 className="text-3xl sm:text-4xl lg:text-[2.75rem] font-bold text-gray-900 leading-[1.15] tracking-tight mb-5">
            {post.title}
          </h1>

          {post.description && (
            <p className="text-lg sm:text-xl text-gray-500 leading-relaxed mb-6 max-w-2xl">
              {post.description}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-400">
            {post.date && (
              <time>{formatDate(post.date)}</time>
            )}
            <span className="text-gray-300">·</span>
            <span>{post.readTime} min read</span>
            {post.tags.length > 0 && (
              <>
                <span className="text-gray-300">·</span>
                <div className="flex flex-wrap gap-2">
                  {post.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2.5 py-0.5 text-xs font-medium bg-[#006fb4]/8 text-[#006fb4] rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Table of Contents (desktop sidebar) */}
      <TableOfContents headings={headings} />

      {/* Article Content */}
      <article data-article-content className="max-w-3xl mx-auto px-4 pb-16">
        <div className="blog-article-body prose prose-lg prose-gray max-w-none
          prose-headings:font-bold prose-headings:text-gray-900 prose-headings:tracking-tight
          prose-h2:text-[1.6rem] prose-h2:mt-14 prose-h2:mb-5
          prose-h3:text-xl prose-h3:mt-10 prose-h3:mb-4
          prose-p:text-gray-700
          prose-a:text-[#006fb4] prose-a:no-underline hover:prose-a:underline prose-a:font-medium
          prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-[0.85em] prose-code:font-mono prose-code:before:content-none prose-code:after:content-none
          prose-pre:bg-transparent prose-pre:p-0 prose-pre:m-0
          prose-ul:list-disc prose-ol:list-decimal
          prose-li:text-gray-700
          prose-img:rounded-xl prose-img:shadow-md
          prose-strong:text-gray-900
          prose-hr:border-gray-200 prose-hr:my-12
        ">
          <MarkdownRenderer content={post.content} />
        </div>

        {/* Footer CTA — Premium */}
        <div className="mt-20 pt-10 border-t border-gray-100">
          <div className="relative overflow-hidden bg-gradient-to-br from-[#006fb4] via-[#005a94] to-[#00476e] rounded-2xl p-10 sm:p-12 text-center text-white">
            {/* Subtle noise texture */}
            <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")', backgroundSize: '128px 128px' }} />
            {/* Decorative circles */}
            <div className="absolute -top-12 -right-12 w-48 h-48 bg-white/5 rounded-full" />
            <div className="absolute -bottom-8 -left-8 w-32 h-32 bg-white/5 rounded-full" />
            <div className="relative">
              <h3 className="text-2xl sm:text-3xl font-bold mb-3">
                Try FundFish Free
              </h3>
              <p className="text-blue-100/80 mb-6 text-lg max-w-md mx-auto">
                AI-powered grant discovery and proposal writing for nonprofits. Find funding faster.
              </p>
              <Link
                href="/signup"
                className="inline-block px-8 py-3.5 bg-white text-[#006fb4] font-semibold rounded-xl hover:bg-blue-50 hover:shadow-lg transition-all duration-200 text-base"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </article>

      {/* Share Buttons */}
      <ShareButtons title={post.title} url={articleUrl} />

      {/* Bottom padding for mobile share bar */}
      <div className="lg:hidden h-20" />
    </div>
  )
}
