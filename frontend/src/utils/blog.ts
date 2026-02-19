import fs from 'fs'
import path from 'path'
import matter from 'gray-matter'

export interface BlogPost {
  slug: string
  title: string
  date: string
  description: string
  tags: string[]
  content: string
}

export interface BlogPostMeta {
  slug: string
  title: string
  date: string
  description: string
  tags: string[]
}

const BLOG_DIR = path.join(process.cwd(), '..', 'blog')

export function getAllPosts(): BlogPostMeta[] {
  // Check if blog directory exists
  if (!fs.existsSync(BLOG_DIR)) {
    return []
  }

  const files = fs.readdirSync(BLOG_DIR)
  
  const posts = files
    .filter(file => file.endsWith('.md') && file !== 'README.md')
    .map(file => {
      const slug = file.replace(/\.md$/, '')
      const filePath = path.join(BLOG_DIR, file)
      const fileContent = fs.readFileSync(filePath, 'utf-8')
      const { data } = matter(fileContent)
      
      return {
        slug,
        title: data.title || slug,
        date: data.date || '',
        description: data.description || '',
        tags: data.tags || [],
      }
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  
  return posts
}

export function getPostBySlug(slug: string): BlogPost | null {
  const filePath = path.join(BLOG_DIR, `${slug}.md`)
  
  if (!fs.existsSync(filePath)) {
    return null
  }
  
  const fileContent = fs.readFileSync(filePath, 'utf-8')
  const { data, content } = matter(fileContent)
  
  return {
    slug,
    title: data.title || slug,
    date: data.date || '',
    description: data.description || '',
    tags: data.tags || [],
    content,
  }
}

export function getAllPostSlugs(): string[] {
  if (!fs.existsSync(BLOG_DIR)) {
    return []
  }

  const files = fs.readdirSync(BLOG_DIR)
  
  return files
    .filter(file => file.endsWith('.md') && file !== 'README.md')
    .map(file => file.replace(/\.md$/, ''))
}
