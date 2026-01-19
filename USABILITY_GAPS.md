# Usability Gaps - What's Still Needed

## Critical Blockers (Must Fix Before Launch)

### 1. **Auth & Team Access** ⛔
**Problem**: System assumes 1 user = 1 organization, but nonprofits need:
- Multiple staff editing the same profile
- Role-based permissions (who can edit vs view)
- Organization ownership/admin designation
- Profile is currently tied to `user_id`, not organization

**Impact**: Cannot be used by real teams
**Effort**: Medium (2-3 hours)

**What to build**:
```sql
-- Add to organization_config
- owner_id (who created it)
- organization_members (team access)
- roles (admin, editor, viewer)

-- Or create separate table
organization_members:
  - org_id, user_id, role, created_at
```

**Frontend**:
- "Share Profile" button → invite team members
- Role selector (who can edit vs view)
- Member list with remove option

---

### 2. **Profile Not Connected to Search** ⛔
**Problem**: Profile exists but:
- Not verified that actual grant searches use it
- Users don't see they're getting org-specific results
- No visual feedback that profile matters
- Could be wasting effort if search doesn't actually use it

**Impact**: No value proposition - users won't complete profile if they don't see better results
**Effort**: Low (testing + 1 hour integration fix if needed)

**What to verify**:
1. Search actual grants with org profile
2. Compare results WITH vs WITHOUT profile
3. Log shows org-aware scoring happening
4. Results visibly different (different grants, different order)

**Frontend addition**:
```
"🎯 Using your organization profile for smarter matches"
- Show which fields are being used for this search
- "This grant matched because: workforce focus + budget fit + location"
```

---

### 3. **Form UX/Validation** ⛔
**Problem**: 50 fields with no guidance:
- Users don't know which are required
- No context about why each field matters
- No validation (can submit budget as text)
- Gets overwhelming

**Impact**: High abandonment rate
**Effort**: Medium (2-3 hours)

**Quick fixes**:
```tsx
// Mark required fields
<label>Organization Name *</label>  // * = required

// Add help text
<input
  placeholder="e.g., $500,000"
  title="Help text explaining this field"
/>

// Field-level validation
- Budget must be number > 0
- Email must be valid
- Years established must be 1900-2026
- Grant size min < max

// Group related fields
<fieldset>
  <legend>Basic Information</legend>
  ...
</fieldset>
```

---

## High Priority (Should Fix Soon)

### 4. **Profile Progress Indicator**
**Problem**: Users don't know if profile is "complete enough"
- Show 40% done vs 90% done
- Guide them to next important field
- Encourage completion

**Impact**: More complete profiles = better matching
**Effort**: Low (1-2 hours)

**Implementation**:
```tsx
<ProgressBar value={42} max={100} />
<p>You've completed 21 of 50 fields</p>
<button>Complete Next Essential Field</button>
```

---

### 5. **Mobile Responsiveness**
**Problem**: Settings page probably broken on mobile
- Forms stack vertically?
- Tabs hard to tap?
- Arrays (add program) awkward?

**Impact**: Nonprofits use phones/tablets
**Effort**: 1-2 hours

**Test**:
```bash
# Check mobile view
iPhone 12: 390px wide
iPad: 768px wide
```

---

### 6. **Save Draft / Partial Completion**
**Problem**: Can't save incomplete profile
- Users might fill out partially, come back later
- All-or-nothing form submission is frustrating
- Lose work if browser crashes

**Impact**: Users abandon half-way
**Effort**: Low (already using Supabase, should auto-save)

**Implementation**:
```tsx
// Auto-save as they type (debounced)
const handleChange = debounce((field, value) => {
  supabase.from('organization_config').update({ [field]: value }).execute()
  showToast("Saved ✓")
}, 1000)

// Or explicit "Save Draft" button
<button onClick={saveAll}>💾 Save Progress</button>
```

---

### 7. **Required vs Optional Field Clarity**
**Problem**: No clear which fields matter
- 50 fields feels like 50 required fields
- User doesn't know "name, mission, focus area" are essential
- Other fields are for advanced matching

**Impact**: Decision paralysis
**Effort**: 1 hour

**Solution**:
```tsx
// Categorize clearly
const REQUIRED_FIELDS = ['name', 'mission', 'primary_focus_area', ...]
const RECOMMENDED_FIELDS = ['programs', 'target_populations', ...]
const OPTIONAL_FIELDS = ['logo_url', 'expansion_plans', ...]

// UI feedback
<input required />  // HTML5 validation
<label>Organization Name <span className="text-red-600">*</span></label>
<p className="text-gray-500">Optional field</p>
```

---

## Medium Priority (Would Be Nice)

### 8. **Sector Templates**
**Problem**: Starting with blank form is overwhelming
- Education nonprofits should see education-relevant fields
- Healthcare nonprofits see health fields
- Reduce to ~20 fields instead of 50

**Effort**: Medium (2-3 hours)

**Implementation**:
```tsx
// Step 1: Choose sector
<select>
  <option>Select your sector...</option>
  <option value="education">Education & Youth</option>
  <option value="health">Health & Human Services</option>
  <option value="arts">Arts & Culture</option>
  <option value="environment">Environment</option>
  <option value="economic">Economic Development</option>
  <option value="housing">Housing & Homelessness</option>
</select>

// Step 2: Show sector-specific template
// - Show only relevant fields
// - Pre-select appropriate focus areas
// - Example values from similar orgs
```

---

### 9. **Field-Level Help & Examples**
**Problem**: Users don't understand what to enter
- "Custom search keywords" - what does that mean?
- "Matching fund capacity" - how much should we say?
- No examples provided

**Effort**: Low but time-consuming (3-4 hours to write all help text)

**Solution**:
```tsx
<div className="help-tooltip">
  <label>
    Custom Search Keywords
    <HelpIcon title="..." />
  </label>
  <input
    placeholder="e.g., 'trauma-informed', 'LGBTQ-affirming'"
    title="Words that describe your approach that funders care about"
  />
  <div className="example">
    💡 Example: If you use trauma-informed practices, add 'trauma-informed'
    to find funders who specifically value this approach
  </div>
</div>
```

---

### 10. **Quick Wins Toggles**
**Problem**: Users don't see impact of completing each field
- "If I fill this out, what happens?"
- "Will it help me find more grants?"

**Effort**: Low (1-2 hours) - just UX, no backend changes

**Solution**:
```
"Complete these fields for better matches:"

☐ Key Programs (would match 15 more grants)
☐ Target Populations (would match 8 more grants)
☐ Custom Keywords (would match 3 more grants)

📈 Impact: Completing 3 fields → see 26 additional matching grants
```

---

### 11. **In-App Help/Tooltips**
**Problem**: Users have questions mid-form
- Can't leave form to read docs
- No context-specific help

**Effort**: Low-medium (2-3 hours)

**Solution**:
```tsx
// Collapsible help section
<Accordion>
  <AccordionItem title="Need help with this field?">
    <div>
      <p>This field helps us find funders who...</p>
      <p>Example: ABC Nonprofit entered "{example}"</p>
      <a href="/help">Read full guide →</a>
    </div>
  </AccordionItem>
</Accordion>
```

---

## Lower Priority (Nice to Have)

### 12. **Data Import from 990 Form**
- IRS 990 form has organization data
- Could auto-fill: name, EIN, mission, annual budget
- **Effort**: High (2-3 days) - need 990 parser
- **Impact**: Saves time for organizations

---

### 13. **Onboarding Flow**
- New user lands on blank profile
- Get asked: "How many employees? What's your mission?" (3-5 questions)
- Auto-generate starter profile
- Then offer to edit/expand
- **Effort**: Medium (3-4 hours)
- **Impact**: 50% more completions

---

### 14. **Matching Quality Feedback**
- Track: did users apply to recommendations?
- Track: did they get funded?
- Show: "These recommendations got us 2 grants last year"
- **Effort**: Medium (2-3 days) - requires tracking
- **Impact**: Proves value, improves algorithm

---

### 15. **Team Collaboration Features**
- Comments on fields
- Change history
- Task assignments
- "John, please fill out programs section"
- **Effort**: High (3-4 days)
- **Impact**: Great UX for teams

---

## Testing That Must Happen

### Before Any Users See This:
- [ ] **Real nonprofit fills profile** - Have someone non-technical try it
- [ ] **Mobile testing** - Works on iPhone/iPad?
- [ ] **Form submission works** - Data actually saves to Supabase?
- [ ] **Search uses profile** - Do org-specific searches work?
- [ ] **Results are different** - Organization A gets different results than B?
- [ ] **Help text is clear** - Do users understand each field?

### One User Test (30 min):
1. Give nonprofit the form
2. Watch them fill it out without help
3. Where do they get confused?
4. Which fields do they skip?
5. How long does it take?
6. Do they see the value?

---

## Realistic Launch Phases

### Phase 1: Minimum Viable (Week 1-2)
**What to fix before ANY users see it:**
- ✅ Team/multi-user access (critical blocker)
- ✅ Verify search actually uses profile (critical blocker)
- ✅ Form validation (don't let bad data in)
- ✅ Required field markers
- ✅ Mobile responsive
- ✅ One real nonprofit beta test

**Timeline**: 2-3 days
**Effort**: Low-medium

---

### Phase 2: Initial Launch (Week 3-4)
**With these additions:**
- Profile progress indicator
- Save draft functionality
- Help text for major fields
- Quick-start templates
- In-app help icons

**Timeline**: 1 week
**Effort**: Medium

---

### Phase 3: Growth & Feedback (Month 2)
**Based on actual user feedback:**
- Fix whatever confuses real users
- Add requested features
- Improve matching algorithm based on what works

**Timeline**: Ongoing
**Effort**: Varies

---

## Priority Checklist

🔴 **Do Before Launch**:
- [ ] Team access (multiple users per org)
- [ ] Verify matching works end-to-end
- [ ] Form validation
- [ ] Required field clarity
- [ ] Mobile responsive
- [ ] Real user test (watch someone non-technical use it)

🟡 **Do Within 2 Weeks**:
- [ ] Progress indicator
- [ ] Save draft
- [ ] Help text
- [ ] Quick templates
- [ ] Better error messages

🟢 **Nice to Have**:
- [ ] 990 import
- [ ] Team collaboration features
- [ ] Analytics/feedback loop
- [ ] Advanced matching refinements

---

## Quick Assessment

**Current State**: System is technically complete but UX needs work

**Biggest Risk**: User tries form, gives up halfway → abandonment

**Biggest Win**: One required field improvement could 2x completion rate

**Recommended Path**:
1. Fix team access (1 day)
2. Verify search works (2 hours)
3. Fix form UX (validation, required fields, help) (1 day)
4. One real user test (2 hours)
5. Quick fixes based on feedback (3-4 hours)
6. **Launch** (by end of week)

**Time estimate**: 3-4 days for launch-ready version
