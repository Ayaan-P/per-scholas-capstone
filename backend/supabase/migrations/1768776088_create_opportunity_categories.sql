-- Create opportunity categories table for flexible categorization
CREATE TABLE opportunity_categories (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  color_hex TEXT DEFAULT '#3B82F6',
  icon TEXT,
  is_active BOOLEAN DEFAULT true,
  display_order INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create category keywords mapping
CREATE TABLE category_keywords (
  id SERIAL PRIMARY KEY,
  category_id INT NOT NULL REFERENCES opportunity_categories(id) ON DELETE CASCADE,
  keyword TEXT NOT NULL,
  weight FLOAT DEFAULT 1.0,
  is_required BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add unique constraint on category_id + keyword
CREATE UNIQUE INDEX idx_category_keyword_unique ON category_keywords(category_id, keyword);

-- Create category search prompts (customizable prompts for each category)
CREATE TABLE category_search_prompts (
  id SERIAL PRIMARY KEY,
  category_id INT NOT NULL UNIQUE REFERENCES opportunity_categories(id) ON DELETE CASCADE,
  prompt_template TEXT NOT NULL,
  focus_areas TEXT[] DEFAULT ARRAY[]::TEXT[],
  min_funding INT DEFAULT 50000,
  deadline_months INT DEFAULT 6,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add category reference to scraped_grants
ALTER TABLE scraped_grants
ADD COLUMN category_id INT REFERENCES opportunity_categories(id) ON DELETE SET NULL;

-- Add category reference to saved_opportunities
ALTER TABLE saved_opportunities
ADD COLUMN category_id INT REFERENCES opportunity_categories(id) ON DELETE SET NULL;

-- Create index for category filtering
CREATE INDEX idx_scraped_grants_category ON scraped_grants(category_id);
CREATE INDEX idx_saved_opportunities_category ON saved_opportunities(category_id);

-- Insert default categories
INSERT INTO opportunity_categories (name, description, color_hex, display_order) VALUES
('Workforce Development', 'Job training, apprenticeships, workforce readiness programs', '#3B82F6', 1),
('STEM Education', 'Science, Technology, Engineering, Math training and education', '#8B5CF6', 2),
('Nonprofit Capacity', 'General nonprofit operations, capacity building, infrastructure', '#10B981', 3),
('Small Business', 'Small business development, entrepreneurship, business grants', '#F59E0B', 4),
('Women-Focused', 'Programs specifically for women entrepreneurs and professionals', '#EC4899', 5),
('Minority-Focused', 'Programs for underrepresented communities and minorities', '#06B6D4', 6),
('Veterans', 'Programs for military veterans and veteran-owned businesses', '#6366F1', 7),
('Community Development', 'Local economic development, community improvement initiatives', '#14B8A6', 8),
('Sustainability/Green', 'Environmental, renewable energy, sustainability initiatives', '#22C55E', 9),
('Healthcare', 'Healthcare, medical research, public health programs', '#EF4444', 10);

-- Insert keywords for each category
INSERT INTO category_keywords (category_id, keyword, weight) VALUES
-- Workforce Development (1)
((SELECT id FROM opportunity_categories WHERE name = 'Workforce Development'), 'workforce development', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Workforce Development'), 'job training', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Workforce Development'), 'apprenticeship', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Workforce Development'), 'career development', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'Workforce Development'), 'employment', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'Workforce Development'), 'skills training', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'Workforce Development'), 'job readiness', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'Workforce Development'), 'wage growth', 0.8),

-- STEM Education (2)
((SELECT id FROM opportunity_categories WHERE name = 'STEM Education'), 'STEM', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'STEM Education'), 'technology training', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'STEM Education'), 'cybersecurity', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'STEM Education'), 'software development', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'STEM Education'), 'cloud computing', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'STEM Education'), 'IT training', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'STEM Education'), 'coding bootcamp', 1.0),

-- Nonprofit Capacity (3)
((SELECT id FROM opportunity_categories WHERE name = 'Nonprofit Capacity'), 'nonprofit', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Nonprofit Capacity'), '501(c)(3)', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Nonprofit Capacity'), 'capacity building', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'Nonprofit Capacity'), 'organizational development', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'Nonprofit Capacity'), 'nonprofit support', 1.0),

-- Small Business (4)
((SELECT id FROM opportunity_categories WHERE name = 'Small Business'), 'small business', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Small Business'), 'entrepreneurship', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Small Business'), 'business development', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'Small Business'), 'startup', 1.0),

-- Women-Focused (5)
((SELECT id FROM opportunity_categories WHERE name = 'Women-Focused'), 'women entrepreneurs', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Women-Focused'), 'women-owned', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Women-Focused'), 'women in technology', 1.0),

-- Minority-Focused (6)
((SELECT id FROM opportunity_categories WHERE name = 'Minority-Focused'), 'minority', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Minority-Focused'), 'underrepresented', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Minority-Focused'), 'disadvantaged', 1.0),

-- Veterans (7)
((SELECT id FROM opportunity_categories WHERE name = 'Veterans'), 'veteran', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Veterans'), 'military', 1.0),

-- Community Development (8)
((SELECT id FROM opportunity_categories WHERE name = 'Community Development'), 'community development', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Community Development'), 'economic development', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'Community Development'), 'community improvement', 1.0),

-- Sustainability (9)
((SELECT id FROM opportunity_categories WHERE name = 'Sustainability/Green'), 'sustainability', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Sustainability/Green'), 'green', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Sustainability/Green'), 'renewable energy', 1.0),

-- Healthcare (10)
((SELECT id FROM opportunity_categories WHERE name = 'Healthcare'), 'healthcare', 1.5),
((SELECT id FROM opportunity_categories WHERE name = 'Healthcare'), 'health', 1.0),
((SELECT id FROM opportunity_categories WHERE name = 'Healthcare'), 'medical', 1.0);

-- Insert default search prompts for each category
INSERT INTO category_search_prompts (category_id, prompt_template, focus_areas, min_funding) VALUES
((SELECT id FROM opportunity_categories WHERE name = 'Workforce Development'),
 'Find state and local workforce development, job training, and apprenticeship funding opportunities',
 ARRAY['job training', 'apprenticeships', 'workforce readiness', 'career development'], 25000),

((SELECT id FROM opportunity_categories WHERE name = 'STEM Education'),
 'Find STEM education, technology training, and coding bootcamp funding opportunities',
 ARRAY['cybersecurity training', 'software development', 'cloud computing', 'IT certifications'], 50000),

((SELECT id FROM opportunity_categories WHERE name = 'Nonprofit Capacity'),
 'Find nonprofit grants for capacity building, operations, and organizational development',
 ARRAY['nonprofit support', 'capacity building', 'organizational effectiveness', 'management systems'], 10000),

((SELECT id FROM opportunity_categories WHERE name = 'Small Business'),
 'Find small business development, entrepreneurship, and startup funding opportunities',
 ARRAY['small business development', 'entrepreneurial support', 'business growth', 'startup funding'], 25000),

((SELECT id FROM opportunity_categories WHERE name = 'Women-Focused'),
 'Find funding for women entrepreneurs, women-owned businesses, and women in technology',
 ARRAY['women entrepreneurship', 'women-owned business', 'women in technology', 'female leadership'], 20000),

((SELECT id FROM opportunity_categories WHERE name = 'Minority-Focused'),
 'Find funding for underrepresented communities, minority-owned businesses, and minority professionals',
 ARRAY['minority business', 'underrepresented communities', 'diversity initiatives', 'inclusion programs'], 20000),

((SELECT id FROM opportunity_categories WHERE name = 'Veterans'),
 'Find funding for veterans, veteran-owned businesses, and military transition programs',
 ARRAY['veteran support', 'veteran employment', 'military transition', 'veteran-owned business'], 20000),

((SELECT id FROM opportunity_categories WHERE name = 'Community Development'),
 'Find community development, local economic development, and neighborhood improvement funding',
 ARRAY['economic development', 'community improvement', 'neighborhood revitalization', 'local initiatives'], 30000),

((SELECT id FROM opportunity_categories WHERE name = 'Sustainability/Green'),
 'Find sustainability, green energy, and environmental conservation funding opportunities',
 ARRAY['renewable energy', 'sustainability', 'environmental conservation', 'green infrastructure'], 50000),

((SELECT id FROM opportunity_categories WHERE name = 'Healthcare'),
 'Find healthcare, medical research, and public health funding opportunities',
 ARRAY['healthcare delivery', 'medical research', 'public health', 'health equity'], 50000);
