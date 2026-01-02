import { useMemo, useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import mockData from "../mock/analysis.json"
import SentimentBadge from "../components/SentimentBadge"
import InsightCard from "../components/InsightCard"
import TranscriptBlock from "../components/TranscriptBlock"
import { exportPDF } from "../utils/exportPdf"
import { useRef } from "react"

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
    const pdfRef = useRef(null)

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

        // 1. Key Insights (Strict Separation)
        const keyInsights = (insights.key_insights || []).map(i => ({
            text: i.text,
            type: i.type
        }))

        // 2. Action Plan (Decisions + Actions)
        let actionPlan = []
        if (mode === "sales") {
            const objections = (insights.objections || []).map(o => `Objection: ${o.text} (${o.type})`)
            const actions = (insights.recommended_actions || []).map(a => `Recommendation: ${a}`)
            actionPlan = [...objections, ...actions]
        } else {
            const decisions = (insights.decisions || []).map(d => `Decision: ${d.text}`)
            const actions = (insights.action_items || []).map(a => `Action: ${a.task} ${a.owner !== "Unassigned" ? `(@${a.owner})` : ""}`)
            actionPlan = [...decisions, ...actions]
        }

        // Calculate average sentiment
        const totalSent = segments.reduce((acc, s) => acc + (s.sentiment || 0), 0)
        const avgSent = segments.length ? (totalSent / segments.length) : 0

        // Extract Summary & Explicit Sentiment Label
        // Sales: overall_call_sentiment
        // Meeting: overall_sentiment_label
        let summaryText = ""
        let explicitSentiment = null

        if (mode === "sales") {
            summaryText = `Overall Call Sentiment: ${insights.overall_call_sentiment || "Neutral"}. Detected ${insights.objections?.length || 0} objections.`
            explicitSentiment = insights.overall_call_sentiment
        } else {
            summaryText = insights.summary || "No summary available."
            explicitSentiment = insights.overall_sentiment_label || "Neutral / Focused"
        }

        return {
            mode: mode,
            duration: formattedDuration,
            summary: summaryText,
            sentimentScore: avgSent,
            sentimentLabel: explicitSentiment,
            // meetingHealth removed from UI data structure
            quality: insights.quality, // NEW: Quality Object
            keyInsights: keyInsights, // Object array
            actionPlan: actionPlan,   // String array
            transcript: mappedTranscript
        }

    }, [location.state, persistedData])

    // Wait for data resolution
    if (!displayData) return null

    const isSales = displayData.mode === "sales"
    const data = displayData // Alias

    // 1. MODE BADGE (Locked)
    const modeLabel = isSales ? "Sales Call" : "Meeting";
    const modeColor = isSales ? "bg-purple-50 text-purple-700 border-purple-100" : "bg-blue-50 text-blue-700 border-blue-100";
    const modeDot = isSales ? "bg-purple-500" : "bg-blue-500";

    // 2. HEALTH BADGE (New, Separate)
    // Mapping: good -> On Track, at_risk -> At Risk, uncertain -> Needs Attention
    // 2. HEALTH BADGE (Removed from Header as per UX request)
    // Meeting Health is now only used in logic/insights, not as a badge.

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

            <div className="max-w-5xl mx-auto px-6 py-6 flex justify-end">
                <button
                    onClick={() => exportPDF(pdfRef)}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition shadow-sm font-medium no-print"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Export PDF
                </button>
            </div>

            <div ref={pdfRef} id="pdf-content" className="bg-gray-50 pb-12">
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

                        {/* Status Badges Section */}
                        <div className="flex items-center gap-3">
                            {/* BADGE 1: MODE (Infrastructure) */}
                            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border ${modeColor}`}>
                                <span className={`w-2 h-2 rounded-full ${modeDot}`}></span>
                                {modeLabel}
                            </span>

                            {/* BADGE 3: SENTIMENT (Context only) */}
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
                        <p className="text-gray-600 leading-relaxed text-lg mb-4">
                            {data.summary}
                        </p>

                        {/* Quiet Quality Indicator */}
                        {data.quality && (
                            <div className="text-sm text-gray-500 font-medium border-t border-gray-100 pt-3 flex items-center gap-2">
                                <span>{isSales ? "Sales" : "Meeting"} Quality:</span>
                                <span className={`px-2 py-0.5 rounded text-xs tracking-wide ${data.quality.label === "High" ? "bg-gray-100 text-gray-700" :
                                    data.quality.label === "Low" ? "bg-gray-50 text-gray-500" :
                                        "bg-gray-50 text-gray-600"
                                    }`}>
                                    {data.quality.label}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Key Insights Grid (Conditionally Rendered) */}
                    {data.keyInsights.length > 0 && (
                        <div>
                            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                Key Insights
                            </h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
                                {data.keyInsights.map((item, i) => (
                                    <div key={i} className="h-full">
                                        <InsightCard text={item.text} type={item.type} />
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Action Plan (Separate Section) */}
                    {data.actionPlan.length > 0 && (
                        <div>
                            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                                </svg>
                                Action Plan
                            </h2>
                            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                                <ul className="space-y-3">
                                    {data.actionPlan.map((item, i) => (
                                        <li key={i} className="flex items-start gap-3">
                                            <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0"></div>
                                            <span className="text-gray-700">{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}
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
            </div >
        </div >
    )
}