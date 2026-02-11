"""
Adaptive Scoring System - Self-Improving Grant Matching

Each org's agent learns what grants they actually care about and evolves
its own scoring algorithm based on feedback.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import importlib.util


class AdaptiveScoringAgent:
    """
    Per-org scoring agent that learns and improves over time.
    
    The agent:
    1. Starts with a baseline scoring approach
    2. Tracks feedback (saves, dismissals, applications)
    3. Experiments with new scoring methods
    4. Measures accuracy (precision/recall)
    5. Evolves its scoring code based on what works
    """
    
    def __init__(self, org_id: str, workspace_root: str = None):
        self.org_id = org_id
        
        if workspace_root:
            self.workspace = Path(workspace_root) / org_id
        else:
            self.workspace = Path.home() / "fundfish-scoring" / org_id
        
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        self.scoring_dir = self.workspace / "scoring"
        self.scoring_dir.mkdir(exist_ok=True)
        
        self.experiments_dir = self.scoring_dir / "experiments"
        self.experiments_dir.mkdir(exist_ok=True)
        
        self.feedback_file = self.scoring_dir / "feedback.jsonl"
        self.state_file = self.scoring_dir / "state.json"
        
        self._load_state()
        self._ensure_current_scorer()
    
    def _load_state(self):
        """Load agent state (current approach, stats, etc.)"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                self.state = json.load(f)
        else:
            self.state = {
                "current_version": "baseline",
                "total_scored": 0,
                "feedback_count": 0,
                "last_evolution": None,
                "accuracy_metrics": {},
                "evolution_history": []
            }
            self._save_state()
    
    def _save_state(self):
        """Save agent state"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _ensure_current_scorer(self):
        """Ensure current.py exists (baseline if needed)"""
        current_py = self.scoring_dir / "current.py"
        
        if not current_py.exists():
            # Write baseline scorer
            baseline_code = '''"""
Baseline Scoring Algorithm

6-dimension scoring approach. Agent will evolve this based on feedback.
"""

def score_grant(grant: dict, org_profile: dict, feedback_history: list) -> dict:
    """
    Score a grant 0-100 based on org fit.
    
    Returns:
        {
            "score": int,
            "reasoning": str,
            "confidence": float,
            "breakdown": dict
        }
    """
    score = 0
    breakdown = {}
    reasons = []
    
    # 1. Mission Alignment (30 points)
    mission_keywords = org_profile.get("mission_keywords", [])
    title = grant.get("title", "").lower()
    description = grant.get("description", "").lower()
    
    mission_matches = sum(1 for kw in mission_keywords if kw.lower() in title or kw.lower() in description)
    mission_score = min(30, mission_matches * 10)
    score += mission_score
    breakdown["mission"] = mission_score
    if mission_score > 0:
        reasons.append(f"Mission alignment: {mission_matches} keyword matches")
    
    # 2. Geographic Fit (20 points)
    org_locations = org_profile.get("locations", [])
    grant_focus = grant.get("geographic_focus", "").lower()
    
    if "national" in grant_focus or "nationwide" in grant_focus:
        geo_score = 20
        reasons.append("National scope matches")
    elif any(loc.lower() in grant_focus for loc in org_locations):
        geo_score = 20
        reasons.append("Geographic match")
    else:
        geo_score = 5
    
    score += geo_score
    breakdown["geographic"] = geo_score
    
    # 3. Funding Amount (20 points)
    amount = grant.get("amount", 0)
    target_min = org_profile.get("target_funding_min", 100000)
    target_max = org_profile.get("target_funding_max", 1000000)
    
    if target_min <= amount <= target_max:
        funding_score = 20
        reasons.append(f"Funding ${amount:,} in target range")
    elif amount > target_max:
        funding_score = 15
        reasons.append("Large grant (may be competitive)")
    elif amount >= target_min * 0.5:
        funding_score = 10
        reasons.append("Moderate funding level")
    else:
        funding_score = 5
    
    score += funding_score
    breakdown["funding"] = funding_score
    
    # 4. Deadline Urgency (15 points)
    from datetime import datetime, date
    deadline = grant.get("deadline")
    
    if deadline:
        try:
            deadline_date = date.fromisoformat(deadline) if isinstance(deadline, str) else deadline
            days_until = (deadline_date - date.today()).days
            
            if 14 <= days_until <= 60:
                urgency_score = 15
                reasons.append(f"Optimal timeline ({days_until} days)")
            elif days_until > 60:
                urgency_score = 10
            elif days_until >= 7:
                urgency_score = 8
                reasons.append("Tight deadline - act soon")
            else:
                urgency_score = 0
                reasons.append("Deadline too soon")
        except:
            urgency_score = 5
    else:
        urgency_score = 5
    
    score += urgency_score
    breakdown["urgency"] = urgency_score
    
    # 5. Eligibility (10 points)
    eligibility = grant.get("eligibility_explanation", "").lower()
    org_type = org_profile.get("org_type", "nonprofit").lower()
    
    if "501(c)(3)" in eligibility or "nonprofit" in eligibility:
        if org_type == "nonprofit":
            eligibility_score = 10
            reasons.append("Eligibility confirmed")
        else:
            eligibility_score = 0
            reasons.append("May not be eligible")
    else:
        eligibility_score = 5
    
    score += eligibility_score
    breakdown["eligibility"] = eligibility_score
    
    # 6. Historical Success (5 points)
    funder = grant.get("funder", "")
    past_wins = [f for f in feedback_history if f.get("outcome") == "won" and f.get("funder") == funder]
    
    if past_wins:
        history_score = 5
        reasons.append(f"Past success with {funder}")
    else:
        history_score = 0
    
    score += history_score
    breakdown["history"] = history_score
    
    # Confidence: based on how much data we have
    confidence = min(1.0, len(feedback_history) / 20)
    
    reasoning = " • ".join(reasons) if reasons else "Standard evaluation"
    
    return {
        "score": min(100, score),
        "reasoning": reasoning,
        "confidence": confidence,
        "breakdown": breakdown
    }
'''
            current_py.write_text(baseline_code)
            print(f"[ADAPTIVE] Created baseline scorer for org {self.org_id}")
    
    def load_current_scorer(self):
        """Dynamically load the current scoring function"""
        current_py = self.scoring_dir / "current.py"
        
        spec = importlib.util.spec_from_file_location("current_scorer", current_py)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return module.score_grant
    
    def score_grant(self, grant: dict, org_profile: dict) -> dict:
        """Score a grant using the current approach"""
        try:
            # Load feedback history
            feedback_history = self.get_feedback_history()
            
            # Load and run current scorer
            score_fn = self.load_current_scorer()
            result = score_fn(grant, org_profile, feedback_history)
            
            self.state["total_scored"] += 1
            self._save_state()
            
            return result
        
        except Exception as e:
            print(f"[ADAPTIVE] Scoring error: {e}")
            # Fallback to simple score
            return {
                "score": 50,
                "reasoning": f"Error in scoring: {e}",
                "confidence": 0.0,
                "breakdown": {}
            }
    
    def record_feedback(
        self,
        grant_id: str,
        grant: dict,
        predicted_score: int,
        action: str,  # "saved", "dismissed", "applied", "won", "lost"
        note: Optional[str] = None
    ):
        """Record user feedback for learning"""
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "grant_id": grant_id,
            "funder": grant.get("funder"),
            "amount": grant.get("amount"),
            "predicted_score": predicted_score,
            "action": action,
            "note": note
        }
        
        # Append to feedback log
        with open(self.feedback_file, 'a') as f:
            f.write(json.dumps(feedback) + '\n')
        
        self.state["feedback_count"] += 1
        self._save_state()
        
        # Check if we should evolve
        if self.state["feedback_count"] % 10 == 0:
            self.consider_evolution()
    
    def get_feedback_history(self) -> List[dict]:
        """Load all feedback"""
        if not self.feedback_file.exists():
            return []
        
        feedback = []
        with open(self.feedback_file) as f:
            for line in f:
                if line.strip():
                    feedback.append(json.loads(line))
        return feedback
    
    def calculate_accuracy(self) -> dict:
        """Calculate current scoring accuracy"""
        feedback = self.get_feedback_history()
        
        if len(feedback) < 5:
            return {
                "insufficient_data": True,
                "sample_size": len(feedback)
            }
        
        # Positive actions: saved, applied, won
        # Negative actions: dismissed, lost
        
        true_positives = 0  # High score (>70) + positive action
        false_positives = 0  # High score + negative action
        true_negatives = 0  # Low score (<50) + negative action
        false_negatives = 0  # Low score + positive action
        
        for f in feedback:
            score = f.get("predicted_score", 0)
            action = f.get("action")
            
            is_positive = action in ["saved", "applied", "won"]
            is_negative = action in ["dismissed", "lost"]
            
            if score >= 70:
                if is_positive:
                    true_positives += 1
                elif is_negative:
                    false_positives += 1
            elif score < 50:
                if is_negative:
                    true_negatives += 1
                elif is_positive:
                    false_negatives += 1
        
        total = true_positives + false_positives + true_negatives + false_negatives
        
        if total == 0:
            precision = recall = 0
        else:
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        
        return {
            "precision": precision,
            "recall": recall,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "true_negatives": true_negatives,
            "false_negatives": false_negatives,
            "sample_size": len(feedback)
        }
    
    def consider_evolution(self):
        """Decide if we should try a new scoring approach"""
        accuracy = self.calculate_accuracy()
        
        if accuracy.get("insufficient_data"):
            return
        
        precision = accuracy.get("precision", 0)
        recall = accuracy.get("recall", 0)
        
        # If accuracy is good (>0.7), don't mess with it
        if precision > 0.7 and recall > 0.7:
            print(f"[ADAPTIVE] Accuracy good (P={precision:.2f}, R={recall:.2f}), keeping current approach")
            return
        
        # Otherwise, flag for experimentation
        print(f"[ADAPTIVE] Accuracy suboptimal (P={precision:.2f}, R={recall:.2f}), considering evolution")
        
        # Log the signal
        evolution_note = {
            "timestamp": datetime.now().isoformat(),
            "trigger": "accuracy_check",
            "current_accuracy": accuracy,
            "note": "Ready for agent to experiment with new scoring approaches"
        }
        
        self.state["evolution_history"].append(evolution_note)
        self._save_state()
        
        # Write a task for the agent
        task_file = self.scoring_dir / "evolution_task.md"
        task_file.write_text(f"""# Scoring Evolution Task

**Triggered:** {datetime.now()}
**Current Accuracy:** Precision {precision:.2%}, Recall {recall:.2%}

## Your Mission

Your current scoring approach isn't performing well enough. Users are dismissing grants you scored highly, or saving grants you scored low.

**What to do:**

1. **Analyze feedback** - Read `feedback.jsonl` to see patterns
   - Which grants scored high but got dismissed?
   - Which grants scored low but got saved/applied to?
   - What factors matter most to this org?

2. **Hypothesize improvements** - What could work better?
   - Different weighting?
   - New dimensions (e.g., effort/reward ratio)?
   - Custom logic for this org's specific focus?

3. **Experiment** - Write a new scoring function in `experiments/v{len(self.state['evolution_history'])}.py`
   - Test it against historical grants
   - Calculate what the accuracy would have been
   - Document your reasoning

4. **Deploy if better** - If your experiment beats current accuracy:
   - Copy it to `current.py`
   - Update version in state.json
   - Log why you changed it

**Freedom:**
- You can use any Python libraries
- You can write helper scripts
- You can create ML models
- You can hardcode org-specific rules
- Whatever makes the scores more accurate

**Constraint:**
- Must return same format: `{{"score": int, "reasoning": str, "confidence": float, "breakdown": dict}}`

**Goal:** Maximize precision and recall. Help users find grants they'll actually apply to.
""")
        
        print(f"[ADAPTIVE] Evolution task written to {task_file}")
