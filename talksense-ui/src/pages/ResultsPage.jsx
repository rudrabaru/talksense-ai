import { useState, useEffect } from "react"
import { useLocation, useNavigate } from "react-router-dom"

// Mock data structure (fallback if no data passed)
const mockData = {
    mode: "meeting",
    duration: "32:45",
    summary: "Discussion focused on Q4 product roadmap priorities. Team aligned on mobile-first approach with concerns about timeline feasibility. Three key decisions made regarding feature prioritization.",
    sentimentScore: 0.65,
    sentimentLabel: "Positive / Engaged",
    quality: { label: "High", score: 0.87 },
    keyInsights: [
        { text: "Team unanimously agreed on mobile-first strategy for Q4", type: "decision" },
        { text: "Timeline concerns raised by engineering regarding December delivery", type: "risk" },
        { text: "Budget approval needed from finance before final commitment", type: "blocker" },
        { text: "Strong alignment on customer feedback integration approach", type: "positive" }
    ],
    actionPlan: [
        "Decision: Prioritize mobile app development for Q4 launch",
        "Action: Sarah to prepare detailed timeline analysis (@Sarah)",
        "Action: Mike to schedule budget review meeting with finance (@Mike)",
        "Decision: Weekly sync meetings every Thursday at 2pm"
    ],
    transcript: [
        { time: "00:15", text: "Let's start with the Q4 roadmap discussion. I want to make sure we're all aligned on priorities.", sentiment: 0.7 },
        { time: "01:23", text: "I think we need to be realistic about the timeline. December is really tight for a full mobile release.", sentiment: 0.3 },
        { time: "02:45", text: "Agreed on mobile-first. The customer feedback has been clear on this point.", sentiment: 0.8 },
        { time: "04:12", text: "We'll need budget approval before we can commit resources to this timeline.", sentiment: 0.5 },
        { time: "05:30", text: "I'm confident we can deliver if we scope it properly and get the right support.", sentiment: 0.75 }
    ]
}

function SentimentBadge({ score, label }) {
    const getColor = (s) => {
        if (s >= 0.6) return "bg-teal-50 text-teal-700 border-teal-200"
        if (s >= 0.4) return "bg-gray-50 text-gray-700 border-gray-200"
        return "bg-orange-50 text-orange-700 border-orange-200"
    }

    return (
        <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border ${getColor(score)} transition-smooth`}>
            <span className="w-2 h-2 rounded-full bg-current"></span>
            {label}
        </span>
    )
}

function InsightCard({ text, type, index }) {
    const typeConfig = {
        decision: { color: "indigo", icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z", label: "Decision" },
        risk: { color: "orange", icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z", label: "Risk" },
        blocker: { color: "red", icon: "M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636", label: "Blocker" },
        positive: { color: "teal", icon: "M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5", label: "Insight" }
    }

    const config = typeConfig[type] || typeConfig.positive

    return (
        <div
            className={`bg-white border-l-4 border-${config.color}-400 rounded-xl p-5 shadow-sm hover:shadow-md transition-smooth hover-lift animate-slide-up`}
            style={{ animationDelay: `${index * 100}ms` }}
        >
            <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-lg bg-${config.color}-50 flex items-center justify-center flex-shrink-0`}>
                    <svg className={`w-4 h-4 text-${config.color}-600`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={config.icon} />
                    </svg>
                </div>
                <div className="flex-1 min-w-0">
                    <div className={`text-xs font-bold uppercase tracking-wider text-${config.color}-600 mb-2`}>
                        {config.label}
                    </div>
                    <p className="text-gray-700 leading-relaxed">{text}</p>
                </div>
            </div>
        </div>
    )
}

function TranscriptBlock({ segment, index }) {
    const getSentimentColor = (s) => {
        if (s >= 0.6) return "border-teal-200 bg-teal-50/30"
        if (s >= 0.4) return "border-gray-200 bg-gray-50/30"
        return "border-orange-200 bg-orange-50/30"
    }

    return (
        <div
            className={`p-4 border-l-2 ${getSentimentColor(segment.sentiment)} hover:bg-white/50 transition-smooth animate-fade-in`}
            style={{ animationDelay: `${index * 50}ms` }}
        >
            <div className="flex items-start gap-4">
                <span className="text-xs font-mono text-gray-500 mt-1 flex-shrink-0 w-12">{segment.time}</span>
                <p className="text-gray-700 leading-relaxed flex-1">{segment.text}</p>
            </div>
        </div>
    )
}

export default function ResultsPage() {
    const location = useLocation()
    const navigate = useNavigate()
    const [data, setData] = useState(mockData)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Get data from navigation state
        const analysisData = location.state?.analysisData

        if (analysisData) {
            // Transform backend response to match UI expectations
            const transformedData = {
                mode: analysisData.mode || "meeting",
                duration: analysisData.insights?.duration || "N/A",
                summary: analysisData.insights?.summary || "Analysis complete.",
                sentimentScore: analysisData.insights?.sentiment_score || 0.5,
                sentimentLabel: analysisData.insights?.sentiment_label || "Neutral",
                quality: analysisData.insights?.quality || { label: "Good", score: 0.7 },
                keyInsights: analysisData.insights?.key_insights || [],
                actionPlan: analysisData.insights?.action_plan || [],
                transcript: analysisData.transcript?.segments?.map(seg => ({
                    time: seg.start ? `${Math.floor(seg.start / 60)}:${String(Math.floor(seg.start % 60)).padStart(2, '0')}` : "00:00",
                    text: seg.text || "",
                    sentiment: seg.sentiment_score || 0.5
                })) || []
            }
            setData(transformedData)
        }

        // Simulate loading for smooth transition
        setTimeout(() => setLoading(false), 300)
    }, [location.state])

    const isSales = data.mode === "sales"
    const modeLabel = isSales ? "Sales Call" : "Meeting"
    const modeColor = isSales ? "bg-teal-50 text-teal-700 border-teal-100" : "bg-indigo-50 text-indigo-700 border-indigo-100"
    const modeDot = isSales ? "bg-teal-500" : "bg-indigo-500"

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-16 h-16 mx-auto mb-4">
                        <svg className="animate-spin text-indigo-600" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    </div>
                    <p className="text-gray-600 font-medium">Loading results...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50 animate-fade-in">
            {/* Header - Fixed */}
            <div className="bg-white border-b border-gray-200 sticky top-0 z-20 backdrop-blur-md bg-white/95">
                <div className="mx-auto px-6 lg:px-12 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="relative w-9 h-9">
                            <svg viewBox="0 0 36 36" className="w-full h-full">
                                <rect x="2" y="2" width="32" height="32" rx="8" fill="#4F46E5" />
                                <path d="M12 18h2v-4h-2v4zm4 0h2v-8h-2v8zm4 0h2v-6h-2v6zm4 0h2v-10h-2v10z" fill="white" opacity="0.9" />
                                <path d="M10 22c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2" stroke="white" strokeWidth="1.5" fill="none" opacity="0.7" />
                            </svg>
                        </div>
                        <span className="font-bold text-xl tracking-tight text-gray-900">TalkSense</span>
                    </div>
                    <button
                        onClick={() => navigate('/upload')}
                        className="text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors"
                    >
                        New Analysis →
                    </button>
                </div>
            </div>

            {/* Main Content - Asymmetric Grid Layout */}
            <div className="mx-auto px-6 lg:px-12 xl:px-16 py-8 lg:py-12">
                <div className="grid lg:grid-cols-12 gap-8 lg:gap-12">

                    {/* Left Column - Main Content (8 cols) */}
                    <div className="lg:col-span-8 space-y-8">

                        {/* Header Card */}
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 lg:p-8 animate-slide-up">
                            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-6">
                                <div>
                                    <h1 className="text-3xl lg:text-4xl font-bold text-gray-900 tracking-tight mb-2">
                                        Analysis Complete
                                    </h1>
                                    <p className="text-gray-500 flex items-center gap-2 text-sm">
                                        <span className="relative flex h-2 w-2">
                                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                                            <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
                                        </span>
                                        Processed {new Date().toLocaleDateString()} • {data.duration}
                                    </p>
                                </div>
                                <div className="flex flex-wrap items-center gap-3">
                                    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border ${modeColor}`}>
                                        <span className={`w-2 h-2 rounded-full ${modeDot}`}></span>
                                        {modeLabel}
                                    </span>
                                    <SentimentBadge score={data.sentimentScore} label={data.sentimentLabel} />
                                </div>
                            </div>

                            <div className="prose max-w-none">
                                <p className="text-lg text-gray-700 leading-relaxed">
                                    {data.summary}
                                </p>
                            </div>

                            {data.quality && (
                                <div className="mt-6 pt-6 border-t border-gray-100 flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Analysis Quality</span>
                                    <span className="px-3 py-1 rounded-lg text-sm font-semibold bg-gray-100 text-gray-700">
                                        {data.quality.label}
                                    </span>
                                </div>
                            )}
                        </div>

                        {/* Key Insights */}
                        {data.keyInsights.length > 0 && (
                            <div>
                                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                                    <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                    Key Insights
                                </h2>
                                <div className="grid gap-4">
                                    {data.keyInsights.map((item, i) => (
                                        <InsightCard key={i} text={item.text} type={item.type} index={i} />
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Action Plan */}
                        {data.actionPlan.length > 0 && (
                            <div className="animate-slide-up" style={{ animationDelay: '200ms' }}>
                                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                                    <svg className="w-5 h-5 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                                    </svg>
                                    Action Items
                                </h2>
                                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                                    <ul className="space-y-4">
                                        {data.actionPlan.map((item, i) => (
                                            <li key={i} className="flex items-start gap-3 group">
                                                <div className="mt-1.5 w-5 h-5 rounded-full border-2 border-gray-300 group-hover:border-teal-500 flex-shrink-0 transition-colors"></div>
                                                <span className="text-gray-700 leading-relaxed">{item}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right Sidebar - Transcript (4 cols) */}
                    <div className="lg:col-span-4">
                        <div className="lg:sticky lg:top-24 animate-slide-up" style={{ animationDelay: '100ms' }}>
                            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                                <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                                    <h2 className="font-bold text-gray-900">Transcript</h2>
                                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Timeline
                                    </span>
                                </div>
                                <div className="max-h-[600px] overflow-y-auto">
                                    <div className="divide-y divide-gray-100">
                                        {data.transcript.map((segment, i) => (
                                            <TranscriptBlock key={i} segment={segment} index={i} />
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Quick Actions */}
                            <div className="mt-6 space-y-3">
                                <button className="w-full px-4 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-smooth flex items-center justify-center gap-2 hover-lift active:scale-95">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                    Export Report
                                </button>
                                <button className="w-full px-4 py-3 bg-white text-gray-700 font-semibold rounded-xl border-2 border-gray-200 hover:bg-gray-50 transition-smooth flex items-center justify-center gap-2 hover-lift active:scale-95">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                                    </svg>
                                    Share
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}