import { useMemo, useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import mockData from "../mock/analysis.json"
import SentimentBadge from "../components/SentimentBadge"
import InsightCard from "../components/InsightCard"
import TranscriptBlock from "../components/TranscriptBlock"

function formatTime(seconds) {
    if (seconds === undefined || seconds === null) return ""
    const mins = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

export default function ResultsPage() {
    const location = useLocation()
    const navigate = useNavigate()
    const [persistedData, setPersistedData] = useState(null)

    // Effect: Handle State Persistence & Redirect
    useEffect(() => {
        if (location.state?.data) {
            // New data incoming -> Save to Storage
            localStorage.setItem("ts_analysis_data", JSON.stringify(location.state.data))
            localStorage.setItem("ts_analysis_mode", location.state.mode || "meeting")
        } else {
            // No state -> Try to load from Storage
            const savedData = localStorage.getItem("ts_analysis_data")
            const savedMode = localStorage.getItem("ts_analysis_mode")

            if (savedData) {
                try {
                    setPersistedData({
                        data: JSON.parse(savedData),
                        mode: savedMode || "meeting"
                    })
                } catch (e) {
                    console.error("Failed to parse saved data", e)
                    navigate("/")
                }
            } else {
                // No data at all -> Redirect
                navigate("/")
            }
        }
    }, [location.state, navigate])

    const displayData = useMemo(() => {
        // Source priority: Location State -> Persisted State -> Mock (Fallback)
        const sourceData = location.state?.data || persistedData?.data
        const sourceMode = location.state?.mode || persistedData?.mode

        if (!sourceData) return null

        const { insights, transcript } = sourceData
        const mode = sourceMode || "meeting"
        const segments = transcript.segments || []

        // Helper to format backend segments
        const mappedTranscript = segments.map(s => ({
            time: formatTime(s.start),
            text: s.text,
            sentiment: s.sentiment
        }))

        // Helper to calculate duration
        const lastSegmentEnd = segments.length > 0 ? segments[segments.length - 1].end : 0
        const formattedDuration = formatTime(lastSegmentEnd)

        // Flatten insights to array of strings based on Mode
        let insightList = []
        if (mode === "sales") {
            // Sales Mode: Objections (Objects) -> Strings
            const objections = (insights.objections || []).map(o => `Objection (${o.type}) at ${formatTime(o.time)}: ${o.text}`)
            // Sales Mode: Recommended Actions (Strings)
            const actions = insights.recommended_actions || []

            insightList = [...objections, ...actions]
        } else {
            // Meeting Mode: Decisions (Objects) -> Strings
            const decisions = (insights.decisions || []).map(d => `Decision at ${formatTime(d.time)}: ${d.text}`)
            // Meeting Mode: Action Items (Objects) -> Strings
            const actions = (insights.action_items || []).map(a => `Action: ${a.task} (Deadline: ${a.deadline})`)

            insightList = [...decisions, ...actions]
        }

        // Calculate average sentiment
        const totalSent = segments.reduce((acc, s) => acc + (s.sentiment || 0), 0)
        const avgSent = segments.length ? (totalSent / segments.length) : 0

        // Extract Summary & Explicit Sentiment Label
        // Sales: overall_call_sentiment (or empty)
        // Meeting: summary (String)
        let summaryText = ""
        let explicitSentiment = null

        if (mode === "sales") {
            summaryText = `Overall Call Sentiment: ${insights.overall_call_sentiment || "Neutral"}. Detected ${insights.objections?.length || 0} objections.`
            explicitSentiment = insights.overall_call_sentiment
        } else {
            summaryText = insights.summary || "No summary available."
        }

        return {
            mode: mode,
            duration: formattedDuration,
            summary: summaryText,
            sentimentScore: avgSent,
            sentimentLabel: explicitSentiment,
            insights: insightList.length > 0 ? insightList : ["No significant insights detected."],
            transcript: mappedTranscript
        }

    }, [location.state, persistedData])

    // Wait for data resolution
    if (!displayData) return null

    const isSales = displayData.mode === "sales"
    const data = displayData // Alias

    return (
        <div className="min-h-screen bg-gray-50 pb-12">
            {/* Header */}
            <div className="bg-white border-b sticky top-0 z-20 bg-opacity-80 backdrop-blur-md">
                <div className="max-w-5xl mx-auto px-6 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold shadow-indigo-200 shadow-lg">
                            T
                        </div>
                        <span className="font-bold text-xl tracking-tight text-gray-900">TalkSense</span>
                    </div>
                    <Link
                        to="/"
                        className="text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors"
                    >
                        Start New Analysis &rarr;
                    </Link>
                </div>
            </div>

            <div className="max-w-5xl mx-auto px-6 py-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

                {/* Header & Meta */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                            Analysis Results
                        </h1>
                        <p className="text-gray-500 mt-1 flex items-center gap-2">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                            </span>
                            Processed on {new Date().toLocaleDateString()} • {data.duration || "00:00"}
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border ${isSales ? "bg-purple-50 text-purple-700 border-purple-100" : "bg-blue-50 text-blue-700 border-blue-100"}`}>
                            <span className={`w-2 h-2 rounded-full ${isSales ? "bg-purple-500" : "bg-blue-500"}`}></span>
                            {isSales ? "Sales Call" : "Meeting"}
                        </span>
                        <SentimentBadge score={data.sentimentScore} label={data.sentimentLabel} />
                    </div>
                </div>

                {/* Summary Section */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 md:p-8 hover:shadow-md transition-shadow">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Executive Summary
                    </h2>
                    <p className="text-gray-600 leading-relaxed text-lg">
                        {data.summary}
                    </p>
                </div>

                {/* Insights Grid */}
                <div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Key Insights
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {data.insights.map((item, i) => (
                            <div key={i} className="h-full">
                                <InsightCard text={item} />
                            </div>
                        ))}
                    </div>
                </div>

                {/* Transcript */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
                    <div className="bg-gray-50/80 px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                        <h2 className="font-semibold text-gray-900">Transcript</h2>
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Chronological
                        </span>
                    </div>
                    <div className="divide-y divide-gray-50 p-2">
                        {data.transcript.map((segment, i) => (
                            <TranscriptBlock key={i} segment={segment} />
                        ))}
                    </div>
                </div>

            </div>
        </div>
    )
}