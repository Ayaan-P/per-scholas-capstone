# Launch Roadmap - 3-4 Days to User-Ready

## Overview

The system is technically complete but needs UX improvements before real nonprofits use it. This roadmap gets it to "launch-ready" in 3-4 days.

---

## 🔴 Day 1: Critical Blockers (Team Access)

### Why This First?
- Nonprofits have multiple staff members
- Can't launch if only one person can access profile
- Blocks everything else

### What to Build

**Database Change** (1 hour):
```sql
-- Add owner_id to organization_config
ALTER TABLE organization_config ADD COLUMN owner_id UUID REFERENCES auth.users(id);

-- Create organization_members table
CREATE TABLE organization_members (
    id BIGSERIAL PRIMARY KEY,
    org_id BIGINT REFERENCES organization_config(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('owner', 'editor', 'viewer')),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

-- Update RLS policy
DROP POLICY IF EXISTS "Users can view and update their own organization" ON organization_config;

CREATE POLICY "Users can access organizations they're members of"
    ON organization_config
    FOR ALL
    USING (
        owner_id = auth.uid() OR
        EXISTS (
            SELECT 1 FROM organization_members
            WHERE org_id = organization_config.id
            AND user_id = auth.uid()
        )
    );
```

**Frontend Components** (2-3 hours):

1. **Settings → Team Tab** (new tab):
```tsx
// Show team members
<TeamMembersList>
  - John Smith (Owner)
  - Sarah Jones (Editor)
  - Mike Davis (Viewer)
</TeamMembersList>

// Invite dialog
<InviteDialog>
  <input placeholder="Email address" />
  <select>
    <option value="editor">Can Edit Profile</option>
    <option value="viewer">Can View Only</option>
  </select>
  <button>Send Invite</button>
</InviteDialog>

// Remove button for each member
```

2. **Handle pending invites**:
```tsx
// Create invites table
organization_invites (org_id, email, role, token, expires_at, used_at)

// When invited user signs up/logs in, auto-add to organization
```

**Testing** (30 min):
- [ ] Owner can add team members
- [ ] Invited members can access/edit profile
- [ ] Viewer role can't edit
- [ ] Owner can remove members
- [ ] Multiple users see same data

**Time**: 4-5 hours

---

## 🔴 Day 1-2: End-to-End Search Test (Verify Value Prop)

### Why This Matters?
- If search doesn't actually use org profile, nothing else matters
- Users won't fill out form if they don't see better results
- This is THE blocker for adoption

### What to Test

**1. Manual Integration Test** (1 hour):
```python
# In backend, test script:
import asyncio
from grants_service import GrantsGovService

async def test_end_to_end():
    # Create test org
    org1 = {
        'primary_focus_area': 'workforce-development',
        'custom_search_keywords': ['job-training', 'employment'],
        'annual_budget': 500000
    }

    org2 = {
        'primary_focus_area': 'education',
        'custom_search_keywords': ['school', 'student'],
        'annual_budget': 200000
    }

    # Search with both
    results1 = service.search_grants(user_id="org1")
    results2 = service.search_grants(user_id="org2")

    # Compare:
    # - Results should be different
    # - Scores should reflect org differences
    # - Log should show org-aware scoring

    assert results1[0]['match_score'] != results2[0]['match_score']
    print("✓ End-to-end matching works")

asyncio.run(test_end_to_end())
```

**2. Visual Indicator in UI** (1-2 hours):
```tsx
// Show on dashboard that org profile is being used
<SearchResults>
  <div className="banner-info">
    🎯 Smart Matches
    <p>Using your organization profile to find the best opportunities</p>
    <Link href="/settings">Complete profile for better matches →</Link>
  </div>

  {results.map(grant => (
    <GrantCard>
      <h3>{grant.title}</h3>
      <ScoreBreaddown>
        {grant.org_match_score} match score
        {grant.org_match_details && (
          <details>
            <summary>Why matched?</summary>
            <p>✓ Keyword match: {grant.org_match_details.keywords}</p>
            <p>✓ Funding fit: {grant.org_match_details.funding}</p>
            <p>✓ Geographic: {grant.org_match_details.geographic}</p>
          </details>
        )}
      </ScoreBreaddown>
    </GrantCard>
  ))}
</SearchResults>
```

**3. User Comparison Feature** (optional, 1-2 hours):
```tsx
// Let users toggle org profile matching on/off to see difference
<SearchControls>
  <Toggle>
    <input type="checkbox" checked={useOrgProfile} onChange={toggle} />
    <label>Use my organization profile for matching</label>
  </Toggle>

  {useOrgProfile ? (
    <p>Showing {count} grants matched to your organization</p>
  ) : (
    <p>Showing generic matches (complete profile to see better results)</p>
  )}
</SearchControls>

// Side by side:
// Without profile: ["Grant A", "Grant B", "Grant C", "Grant D"]
// With profile: ["Grant A", "Grant C", "Grant E", "Grant F"]
// → User sees immediate impact
```

**Time**: 2-3 hours

---

## 🟡 Day 2: Form UX & Validation

### Problem
- 50 blank fields = decision paralysis
- No validation = bad data
- No guidance = users don't know what to enter

### Quick Fixes (1-2 hours)

**1. Mark Required Fields**:
```tsx
// In settings page component
const REQUIRED_FIELDS = ['name', 'mission', 'primary_focus_area']
const RECOMMENDED_FIELDS = [...]
const OPTIONAL_FIELDS = [...]

// In each field:
<div>
  <label>
    Organization Name
    {REQUIRED_FIELDS.includes('name') && <span className="text-red-600">*</span>}
  </label>
  <input required={REQUIRED_FIELDS.includes('name')} />
</div>
```

**2. Add Validation**:
```tsx
// Client-side validation before submit
const validateProfile = (data) => {
  const errors = {}

  // Required fields
  if (!data.name) errors.name = "Organization name is required"
  if (!data.mission) errors.mission = "Mission is required"
  if (!data.primary_focus_area) errors.primary_focus_area = "Focus area is required"

  // Type validation
  if (data.annual_budget && isNaN(data.annual_budget)) {
    errors.annual_budget = "Must be a number"
  }
  if (data.contact_email && !data.contact_email.includes('@')) {
    errors.contact_email = "Invalid email"
  }

  // Range validation
  if (data.preferred_grant_size_min && data.preferred_grant_size_max) {
    if (data.preferred_grant_size_min > data.preferred_grant_size_max) {
      errors.preferred_grant_size_min = "Min must be less than max"
    }
  }

  return errors
}

// Show errors
{errors.name && <p className="error">{errors.name}</p>}
```

**3. Add Help Text**:
```tsx
// For 3-5 most confusing fields:
<FieldWithHelp>
  <label>Custom Search Keywords</label>
  <input placeholder="e.g., trauma-informed, LGBTQ-affirming" />
  <HelpText>
    💡 These are special terms that describe your organization's approach.
    Examples: "trauma-informed", "community-led", "asset-based", "evidence-based"
    Learn more →
  </HelpText>
</FieldWithHelp>
```

**Time**: 2-3 hours

---

## 🟡 Day 2-3: Mobile Responsive

### Problem
- Form probably broken on mobile
- Nonprofits use phones/tablets
- Can't launch if mobile doesn't work

### Quick Test & Fixes (2-3 hours)

**Testing**:
```bash
# In Chrome DevTools
1. View → Developer → Toggle Device Toolbar
2. Test on iPhone 12 (390px)
3. Test on iPad (768px)

Check:
- Can tap all buttons easily?
- Forms stack properly?
- Arrays (add program) work?
- Tabs clickable?
- Text readable without zooming?
```

**Common Fixes**:
```tsx
// Responsive grid for tabs
<div className="grid md:grid-cols-2 gap-4">
  {/* Stacks on mobile, 2 cols on tablet */}
</div>

// Larger tap targets
<button className="py-3 px-4 min-w-[48px] min-h-[48px]">
  {/* 48x48px minimum for mobile touch */}
</button>

// Stack complex inputs
<div className="flex flex-col gap-4">
  <input />
  <input />
</div>
```

**Time**: 2-3 hours

---

## 🟢 Day 3: Save Draft & Progress

### Relatively Easy Wins (2-3 hours total)

**1. Auto-Save** (1-2 hours):
```tsx
// Hook to auto-save on change
const useAutoSave = (data, delay = 2000) => {
  const [saved, setSaved] = useState(true)

  useEffect(() => {
    setSaved(false)
    const timer = setTimeout(async () => {
      await supabase.from('organization_config')
        .update(data)
        .eq('id', data.id)
        .execute()
      setSaved(true)
    }, delay)

    return () => clearTimeout(timer)
  }, [data])

  return saved
}

// In form:
const saved = useAutoSave(formData)
<p>{saved ? '✓ Saved' : 'Saving...'}</p>
```

**2. Progress Bar** (1 hour):
```tsx
const calculateProgress = (data) => {
  const required = ['name', 'mission', 'primary_focus_area']
  const filled = required.filter(field => !!data[field]).length
  return (filled / required.length) * 100
}

// Show
<ProgressBar value={progress} max={100} />
<p>You've completed {filledCount} of {totalCount} essential fields</p>
```

**Time**: 2-3 hours

---

## 🟢 Day 4: Real User Test (2-3 hours)

### Find Someone To Test With
- Small nonprofit (5-20 staff)
- Non-technical person (not a developer)
- Actually works in grants or development

### What To Watch For
1. Do they understand the form?
2. Where do they get confused?
3. How long does it take?
4. Do they see why profile matters?
5. Would they actually use this?

### Test Script (15-20 min)
```
"I want you to fill out your organization's profile.
Talk out loud about what you're thinking.
Don't worry about being perfect."

[Watch. Take notes. Don't help.]

Afterwards, ask:
- "Was anything confusing?"
- "What fields were easy/hard?"
- "Did you understand why you were filling it out?"
- "Would you actually use this?"
```

**Timeframe**: 2-3 hours (30 min prep, 20 min test, 1 hour feedback)

---

## 📋 Day-by-Day Schedule

### Day 1 (Full Day):
- Morning: Team access feature (4-5 hours)
- Afternoon: End-to-end search test (2-3 hours)
- **Total**: ~8 hours

### Day 2 (Full Day):
- Morning: Form UX & validation (2-3 hours)
- Afternoon: Mobile responsive testing (2-3 hours)
- Evening: Quick fixes based on testing
- **Total**: ~6-7 hours

### Day 3 (Half Day):
- Morning: Auto-save & progress indicator (2-3 hours)
- Afternoon: Final integration testing
- **Total**: ~3-4 hours

### Day 4 (Half Day):
- Real user test (2-3 hours)
- Note: May reveal quick fixes needed

---

## Success Criteria for Launch

✅ **Before Showing to Real Users**:
- [ ] Multiple team members can access profile
- [ ] Search results visibly different with org profile
- [ ] Form validation prevents bad data
- [ ] Required fields clearly marked
- [ ] Mobile responsive (works on iPhone)
- [ ] Can save partial work
- [ ] One real user test passed (didn't give up)

✅ **Launch Gates**:
- [ ] No data loss on form submit
- [ ] Search actually uses org profile (verified)
- [ ] Error messages are helpful
- [ ] Mobile touch targets are large enough
- [ ] Performance acceptable (< 2 sec form submit)

---

## Post-Launch (Week 2-3)

### Monitor & Iterate
- [ ] Track completion rate (how many orgs fill it out)
- [ ] Track time-to-completion
- [ ] Monitor error rates
- [ ] Collect feedback from early users

### Quick Fixes Based on Real Users
- [ ] Which fields do users skip?
- [ ] Where do they drop off?
- [ ] Which help text is useful?
- [ ] Mobile issues we missed?

### Next Features (If Feedback Warrants)
- [ ] Templates by sector
- [ ] More help content
- [ ] Analytics/feedback loop
- [ ] 990 import

---

## Estimated Total Time

**Detailed Plan**: 3-4 days of solid work
- Day 1: 8 hours
- Day 2: 7 hours
- Day 3: 4 hours
- Day 4: 3 hours (user test)

**Total**: ~20-22 hours

**With 2 developers**: 1.5 weeks
**With 1 developer (you)**: 1 week part-time or 3-4 days full-time

---

## Decision: Start Now or Plan First?

### Start Now If:
- You want to launch within a week
- You have bandwidth for focused work
- You're okay with some rough edges post-launch

### Plan More If:
- You want a higher quality launch
- You want more user feedback first
- You're targeting specific organizations

**Recommendation**: Start Day 1 (team access) immediately. It's the highest-impact blocker.

---

## Dependencies & Blockers

❌ **Blocks Launch**:
- Team access not working
- Search doesn't use org profile
- Mobile doesn't work

⚠️ **Nice to Have for Launch**:
- Perfect form UX
- Progress indicator
- Auto-save
- Fancy onboarding

💡 **Can Iterate Post-Launch**:
- Templates by sector
- Advanced analytics
- Bulk import features
- ML refinement

---

## Questions to Answer Before Starting

1. **Who is your first nonprofit user?**
   - What size? What sector?
   - Can you watch them use it?

2. **How will you measure success?**
   - Completion rate?
   - Better grant matches?
   - More funding raised?

3. **What's your timeline?**
   - Launch end of week?
   - End of month?
   - Driven by a specific nonprofit's needs?

4. **Who's doing the work?**
   - You alone?
   - You + designer?
   - You + developer?
   - You + team?

Answers will shape priorities.

---

## TL;DR - If You Only Do These 3 Things

1. **Fix team access** (Day 1, 4-5 hours) - Can't launch single-user
2. **Verify search works** (Day 1-2, 2-3 hours) - Need value prop
3. **One user test** (Day 4, 3 hours) - See if it's actually usable

Everything else is iteration. These three unblock launch.
