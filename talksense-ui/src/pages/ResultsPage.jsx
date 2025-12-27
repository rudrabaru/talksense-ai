import data from "../mock/analysis.json"
import SentimentBadge from "../components/SentimentBadge"
import InsightCard from "../components/InsightCard"
import TranscriptBlock from "../components/TranscriptBlock"
import { Link, useLocation } from "react-router-dom"

export default function ResultsPage() {
    const location = useLocation()
    // Use the mode passed from UploadPage, fallback to mock data default
    const currentMode = location.state?.mode || data.mode
    const isSales = currentMode === "sales"

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
                            Processed on {new Date().toLocaleDateString()} • {data.duration || "14m 20s"}
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border ${isSales ? "bg-purple-50 text-purple-700 border-purple-100" : "bg-blue-50 text-blue-700 border-blue-100"}`}>
                            <span className={`w-2 h-2 rounded-full ${isSales ? "bg-purple-500" : "bg-blue-500"}`}></span>
                            {isSales ? "Sales Call" : "Meeting"}
                        </span>
                        <SentimentBadge score={data.sentimentScore} />
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