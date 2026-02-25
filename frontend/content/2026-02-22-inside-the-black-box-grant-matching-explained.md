---
title: "Inside the Black Box: How FundFish Scores Grants for Your Nonprofit"
date: "2026-02-22"
description: "We built a Match Profile transparency feature so nonprofits can see exactly why they're seeing the grants they see. Here's how our scoring model actually works."
tags: ["product", "grant-matching", "transparency", "ai"]
author: "FundFish Team"
---

One of the most common questions we get from nonprofits testing FundFish: *"Why is this grant showing up for me?"*

It's a fair question. If an AI system is making recommendations that affect your fundraising strategy, you deserve to understand the reasoning — not just receive a list with mysterious percentage scores.

Today we shipped the **Match Profile** tab in Settings. Here's what it shows and why we built it.

## What's Actually Happening When You Search

When you first complete your organization profile — your focus area, mission statement, target populations, preferred grant sizes — FundFish doesn't just store that data. It builds a personalized search model from it.

Specifically, we derive:

1. **Primary keywords** — High-weight terms pulled from your focus area, mission, and programs. These drive actual searches against the grant database.
2. **Secondary keywords** — Supplementary terms from your target populations and service regions. They broaden discovery without drowning out the core signal.
3. **Scoring weights** — How much each matching factor (keyword alignment, funding range match, deadline feasibility, geographic focus, demographic overlap) contributes to your final match score.
4. **Excluded keywords** — Terms you've flagged as irrelevant. Any grant containing these words gets filtered out before you ever see it.

The Match Profile page now shows you all four, in plain English.

## The Scoring Formula

We score each grant from 0–100 using a weighted combination of factors:

```
Match Score = (keyword_matching × weight_k) 
            + (funding_alignment × weight_f)
            + (deadline_feasibility × weight_d)
            + (demographic_alignment × weight_dem)
            + (geographic_alignment × weight_g)
```

The weights aren't fixed — they adjust based on your profile. If you have strict funding size requirements, `weight_f` goes up. If you're flexible on geography, `weight_g` is lower. A workforce development org in Chicago will have a different scoring model than a rural health nonprofit in Montana.

## Why This Matters More Than You'd Think

Here's something research is starting to confirm: **AI agents search differently than humans**.

A human searching for grants types "education grants for underserved youth Boston." An AI agent — the kind powering FundFish's discovery — generates reasoning-driven queries that look more like: "workforce development opportunity targeting low-income adults, federal or state source, deadline 60+ days, award $50k-$500k, geographic focus northeastern US."

These query patterns are longer, more structured, and more sensitive to the vocabulary you use in your profile. That's why two nonprofits with overlapping missions can see very different results — the specific language in your mission statement becomes the signal.

Knowing this, we built Match Profile so you can tune the signal. If you're seeing too many irrelevant grants: add exclusions. If you're missing opportunities you know exist: check your primary keywords and expand your secondary focus areas.

## The Excluded Keywords Feature

This one's been live since last week (commit `790cc98`), but now it's surfaced in a way you can actually see and interact with.

Here's how it works under the hood:

```python
def should_filter_grant(org_profile, grant):
    excluded = org_profile.get("excluded_keywords") or []
    grant_text = (
        (grant.get("title") or "") + " " + 
        (grant.get("description") or "")
    ).lower()
    
    for keyword in excluded:
        if keyword.lower() in grant_text:
            return True, f"Excluded keyword: '{keyword}'"
    
    return False, None
```

Simple, transparent, fast. Before any scoring happens, grants containing your excluded terms are dropped. You can see which keywords are active in the Match Profile tab, and add/remove them in the Funding tab of Settings.

## What We're Not Doing (Yet)

A few things you'll notice are missing from the current scoring:

- **Semantic similarity** — We're doing keyword matching, not embedding-based semantic search. A grant about "STEM education" won't automatically match an org focused on "technology workforce development" unless you've added the bridging keywords.
- **Funder relationship scoring** — We don't yet know if you've applied to a funder before, or if they've historically funded orgs like yours.
- **Real-time deadline urgency** — Deadline feasibility is calculated, but we don't yet push urgent deadlines to the top proactively.

These are on the roadmap. But before we add more AI, we wanted to make the existing AI legible.

## Try It

Go to **Settings → Match Profile** (the 🎯 tab) to see your current matching configuration. If something looks off, go to the relevant tab and update your profile — changes take effect immediately on your next grant refresh.

We'll keep improving the scoring. But the model will always be visible.

---

*FundFish is an AI fundraising assistant for nonprofits. We're building in public — follow along on our [dev blog](/blog).*
