# PerScholas Fundraising Tool - Frontend Design

## User Experience Strategy

### Target Users
- **Primary**: Per Scholas fundraising team members
- **Technical Level**: Non-technical professionals
- **Daily Tasks**: Finding grants, writing proposals, managing pipeline
- **Pain Points**: Time-consuming manual research, complex proposal writing

### Design Principles
1. **Simplicity First**: One-click actions for complex AI workflows
2. **Clear Visual Hierarchy**: Important information stands out
3. **Actionable Results**: Every output leads to clear next steps
4. **Mobile-Friendly**: Usable on tablets/phones for field work
5. **Familiar Patterns**: Use conventional UI patterns (no learning curve)

## Core User Workflows

### 1. Opportunity Discovery Dashboard
**Primary Use Case**: "Find me new funding opportunities"

**UI Components**:
```
┌─────────────────────────────────────────┐
│ 🔍 Find New Opportunities              │
│                                         │
│ [Quick Search Buttons]                  │
│ • IT Training Grants                    │
│ • Workforce Development                 │
│ • Youth Programs                        │
│ • Custom Search...                      │
│                                         │
│ [Advanced Filters] ▼                    │
│ • Amount Range: $10K - $500K           │
│ • Deadline: Next 60 days               │
│ • Funder Type: Government/Foundation    │
│                                         │
│ [ Start AI Search ] 🚀                 │
└─────────────────────────────────────────┘
```

**Results Display**:
```
┌─────────────────────────────────────────┐
│ 📊 Found 12 Opportunities               │
│ ┌─────────────────────────────────────┐ │
│ │ 🟢 High Match (95%)                 │ │
│ │ DOL Workforce Innovation Grant      │ │
│ │ 💰 $250,000 | 📅 Due: Nov 15       │ │
│ │ "Perfect fit for IT apprenticeship" │ │
│ │ [View Details] [Generate Proposal]  │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ 🟡 Medium Match (78%)               │ │
│ │ Gates Foundation Tech Equity        │ │
│ │ 💰 $100,000 | 📅 Due: Dec 1        │ │
│ │ "Good alignment, competitive"       │ │
│ │ [View Details] [Generate Proposal]  │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 2. Proposal Generation Interface
**Primary Use Case**: "Help me write a proposal for this grant"

**Input Flow**:
```
┌─────────────────────────────────────────┐
│ ✍️ Generate Proposal Draft              │
│                                         │
│ 📎 Upload RFP Document                  │
│ [Choose File] or [Paste URL]           │
│                                         │
│ 🎯 Select Per Scholas Programs          │
│ ☑️ Software Engineering                 │
│ ☑️ Cloud Computing                      │
│ ☐ Data Engineering                      │
│ ☐ Cybersecurity                         │
│                                         │
│ 📍 Target Locations                     │
│ ☑️ Chicago ☑️ New York ☐ Dallas        │
│                                         │
│ [ Generate Draft ] 🤖                  │
│ ⏱️ Expected time: 2-3 minutes           │
└─────────────────────────────────────────┘
```

**Output Display**:
```
┌─────────────────────────────────────────┐
│ 📄 Proposal Draft Generated             │
│                                         │
│ ├─ Executive Summary ✅                 │
│ ├─ Project Description ✅               │
│ ├─ Budget Narrative ⚠️ Needs Review    │
│ ├─ Evaluation Plan ✅                   │
│ └─ Appendices 📎 Templates attached     │
│                                         │
│ 🎯 AI Confidence: 87%                   │
│ 📊 Completeness: 9/10 sections         │
│                                         │
│ [📝 Edit in Google Docs]                │
│ [📧 Share with Team]                    │
│ [💾 Save to Pipeline]                   │
└─────────────────────────────────────────┘
```

### 3. Funding Pipeline Dashboard
**Primary Use Case**: "Show me my opportunities in progress"

```
┌─────────────────────────────────────────┐
│ 📈 My Funding Pipeline                  │
│                                         │
│ 💰 Total Pipeline Value: $1.2M         │
│ 📅 Next Deadline: Nov 15 (3 days)      │
│ ⚡ High Priority: 4 proposals           │
│                                         │
│ [Status Filter: All ▼]                 │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ 🔴 URGENT - Due in 3 days           │ │
│ │ DOL Innovation Grant - $250K        │ │
│ │ Status: Draft Ready (95% complete)  │ │
│ │ [Review Draft] [Submit]             │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ 🟡 In Progress - Due Nov 30         │ │
│ │ Ford Foundation Tech Access - $150K │ │
│ │ Status: Researching (40% complete)  │ │
│ │ [Continue Research] [Get AI Help]   │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Technical Implementation

### Frontend Stack
- **React 18** with TypeScript for type safety
- **Next.js 14** for server-side rendering and routing
- **TailwindCSS** for rapid, consistent styling
- **Shadcn/UI** for pre-built accessible components
- **React Query** for API state management
- **WebSocket** for real-time AI processing updates

### Key Components

#### 1. OpportunityCard Component
```tsx
interface OpportunityCardProps {
  opportunity: {
    id: string;
    title: string;
    funder: string;
    amount: number;
    deadline: Date;
    matchScore: number;
    description: string;
    status: 'new' | 'in-progress' | 'applied';
  };
}

export function OpportunityCard({ opportunity }: OpportunityCardProps) {
  const matchColor = {
    high: 'bg-green-100 text-green-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-red-100 text-red-800'
  };

  return (
    <div className="border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-lg">{opportunity.title}</h3>
        <span className={`px-2 py-1 rounded text-sm ${matchColor[getMatchLevel(opportunity.matchScore)]}`}>
          {opportunity.matchScore}% match
        </span>
      </div>

      <p className="text-gray-600 text-sm mb-3">{opportunity.funder}</p>

      <div className="flex justify-between items-center text-sm text-gray-500 mb-3">
        <span>💰 ${opportunity.amount.toLocaleString()}</span>
        <span>📅 Due: {opportunity.deadline.toLocaleDateString()}</span>
      </div>

      <p className="text-gray-700 text-sm mb-4">{opportunity.description}</p>

      <div className="flex gap-2">
        <Button variant="outline" size="sm">View Details</Button>
        <Button size="sm">Generate Proposal</Button>
      </div>
    </div>
  );
}
```

#### 2. AIProcessingStatus Component
```tsx
export function AIProcessingStatus({ jobId }: { jobId: string }) {
  const [status, setStatus] = useState('starting');
  const [progress, setProgress] = useState(0);
  const [currentTask, setCurrentTask] = useState('');

  useEffect(() => {
    const ws = new WebSocket(`wss://api.perscholas-demo.com/ws/${jobId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data.status);
      setProgress(data.progress);
      setCurrentTask(data.currentTask);
    };

    return () => ws.close();
  }, [jobId]);

  return (
    <div className="bg-blue-50 p-4 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <Spinner className="w-4 h-4" />
        <span className="font-medium">AI Agent Working...</span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <p className="text-sm text-gray-600">{currentTask}</p>
    </div>
  );
}
```

### Page Structure

#### 1. Dashboard Layout
```
Header: [Per Scholas Logo] [Navigation] [User Menu]
Sidebar: [Dashboard] [Find Opportunities] [My Pipeline] [Proposals] [Analytics]
Main: [Current Page Content]
Footer: [Help] [Feedback] [Version]
```

#### 2. Responsive Design
- **Desktop**: Full sidebar navigation, multi-column layouts
- **Tablet**: Collapsible sidebar, card-based layouts
- **Mobile**: Bottom navigation, single-column, swipe gestures

## User Testing Scenarios

### Scenario 1: New Opportunity Discovery
1. User clicks "Find IT Training Grants"
2. AI processes request (2-3 minutes)
3. Results appear with match scores
4. User reviews top opportunity
5. Clicks "Generate Proposal"
6. Draft proposal created in 5 minutes

### Scenario 2: Pipeline Management
1. User checks dashboard for urgent deadlines
2. Sees proposal due in 3 days
3. Reviews AI-generated draft
4. Makes final edits
5. Submits through integrated system

### Scenario 3: Custom Search
1. User wants grants for "cybersecurity training in Chicago"
2. Uses advanced search with filters
3. AI finds specialized opportunities
4. Results ranked by relevance and feasibility

## Success Metrics
- **Task Completion Time**: <5 minutes for opportunity discovery
- **User Adoption**: 100% of fundraising team using within 2 weeks
- **Efficiency Gain**: 80% reduction in manual research time
- **Proposal Quality**: 90%+ first draft completion rate