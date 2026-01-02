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
        </div>
    )
}