import { useEffect, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import SentimentBadge from "../components/SentimentBadge"
import InsightCard from "../components/InsightCard"
import TranscriptBlock from "../components/TranscriptBlock"
import { jsPDF } from "jspdf"

function formatTime(seconds) {
    if (seconds === undefined || seconds === null) return ""
    const mins = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

export default function ResultsPage() {
    const location = useLocation()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [data, setData] = useState({
        mode: "meeting",
        duration: "00:00",
        summary: "",
        sentimentScore: 0,
        sentimentLabel: "Neutral",
        quality: { label: "Medium", score: 5 },
        keyInsights: [],
        actionPlan: [],
        transcript: []
    })

    useEffect(() => {
        // Get data from navigation state
        const analysisData = location.state?.analysisData

        if (analysisData) {
            const mode = analysisData.mode || "meeting"

            // Build action plan based on mode
            let actionPlan = []
            if (mode === "sales") {
                // Sales mode: combine objections and recommendations
                const objections = (analysisData.insights?.objections || []).map(o => `Objection: ${o.text} (${o.type})`)
                const actions = (analysisData.insights?.recommended_actions || []).map(a => `Recommendation: ${a}`)
                actionPlan = [...objections, ...actions]
            } else {
                // Meeting mode: combine decisions and action items
                const decisions = (analysisData.insights?.decisions || []).map(d => `Decision: ${d.text}`)
                const actions = (analysisData.insights?.action_items || []).map(a => `Action: ${a.task}${a.owner && a.owner !== "Unassigned" ? ` (@${a.owner})` : ""}`)
                actionPlan = [...decisions, ...actions]
            }

            // Transform backend response to match UI expectations
            const transformedData = {
                mode: mode,
                duration: analysisData.insights?.duration || formatTime(analysisData.transcript?.segments?.[analysisData.transcript.segments.length - 1]?.end) || "N/A",
                summary: analysisData.insights?.summary || "Analysis complete.",
                sentimentScore: analysisData.insights?.sentiment_score || 0,
                sentimentLabel: analysisData.insights?.overall_sentiment_label || analysisData.insights?.overall_call_sentiment || "Neutral",
                // NEW: Separate meeting_quality and project_risk
                meetingQuality: analysisData.insights?.meeting_quality || { label: "Medium", score: 5 },
                projectRisk: analysisData.insights?.project_risk || { label: "Low", score: 0 },
                // Legacy fallback for old API responses
                quality: analysisData.insights?.quality || analysisData.insights?.meeting_quality || { label: "Medium", score: 5 },
                keyInsights: analysisData.insights?.key_insights || [],
                actionPlan: actionPlan,
                transcript: analysisData.transcript?.segments?.map(seg => ({
                    time: formatTime(seg.start),
                    text: seg.text || "",
                    sentiment: seg.sentiment || 0
                })) || []
            }
            setData(transformedData)
            setLoading(false)
        } else {
            // No data provided, redirect to upload
            setTimeout(() => navigate('/upload'), 100)
        }
    }, [location.state, navigate])

    const isSales = data.mode === "sales"
    const modeLabel = isSales ? "Sales Call" : "Meeting"
    const modeColor = isSales ? "bg-teal-50 text-teal-700 border-teal-100" : "bg-indigo-50 text-indigo-700 border-indigo-100"
    const modeDot = isSales ? "bg-teal-500" : "bg-indigo-500"

    // PDF Export Handler
    const handleExportPDF = () => {
        const doc = new jsPDF()
        const pageWidth = doc.internal.pageSize.getWidth()
        const pageHeight = doc.internal.pageSize.getHeight()
        const margin = 20
        const maxWidth = pageWidth - 2 * margin
        let yPosition = margin

        // Helper function to add text with word wrap
        const addText = (text, fontSize = 10, isBold = false, color = [0, 0, 0]) => {
            doc.setFontSize(fontSize)
            doc.setFont("helvetica", isBold ? "bold" : "normal")
            doc.setTextColor(...color)
            const lines = doc.splitTextToSize(text, maxWidth)

            lines.forEach(line => {
                if (yPosition > pageHeight - margin) {
                    doc.addPage()
                    yPosition = margin
                }
                doc.text(line, margin, yPosition)
                yPosition += fontSize * 0.5
            })
            yPosition += 3
        }

        // Helper function to add a section header
        const addSectionHeader = (title, color = [79, 70, 229]) => {
            yPosition += 5
            doc.setFillColor(...color)
            doc.rect(margin, yPosition - 5, maxWidth, 8, 'F')
            doc.setTextColor(255, 255, 255)
            doc.setFontSize(12)
            doc.setFont("helvetica", "bold")
            doc.text(title, margin + 2, yPosition)
            yPosition += 10
            doc.setTextColor(0, 0, 0)
        }

        // Title
        doc.setFillColor(79, 70, 229)
        doc.rect(0, 0, pageWidth, 35, 'F')
        doc.setTextColor(255, 255, 255)
        doc.setFontSize(24)
        doc.setFont("helvetica", "bold")
        doc.text("TalkSense AI", margin, 20)
        doc.setFontSize(14)
        doc.setFont("helvetica", "normal")
        doc.text("Analysis Report", margin, 28)
        yPosition = 45

        // Metadata
        doc.setTextColor(0, 0, 0)
        doc.setFontSize(10)
        doc.setFont("helvetica", "normal")
        doc.text(`Mode: ${modeLabel}`, margin, yPosition)
        doc.text(`Date: ${new Date().toLocaleDateString()}`, margin + 60, yPosition)
        doc.text(`Duration: ${data.duration}`, margin + 120, yPosition)
        yPosition += 8
        doc.text(`Sentiment: ${data.sentimentLabel}`, margin, yPosition)
        // NEW: Show both Meeting Quality and Project Risk
        if (data.meetingQuality) {
            doc.text(`Meeting Quality: ${data.meetingQuality.label}`, margin + 60, yPosition)
        }
        yPosition += 6
        if (data.projectRisk && data.projectRisk.label !== "Low") {
            doc.text(`Project Risk: ${data.projectRisk.label}`, margin, yPosition)
            yPosition += 6
        }
        yPosition += 5

        // Separator line
        doc.setDrawColor(200, 200, 200)
        doc.line(margin, yPosition, pageWidth - margin, yPosition)
        yPosition += 10

        // Executive Summary
        addSectionHeader("Executive Summary")
        addText(data.summary, 10, false)

        // Key Insights
        if (data.keyInsights.length > 0) {
            addSectionHeader("Key Insights", [245, 158, 11])
            data.keyInsights.forEach((insight, index) => {
                addText(`${index + 1}. [${insight.type}] ${insight.text}`, 10, false)
            })
        }

        // Action Plan
        if (data.actionPlan.length > 0) {
            addSectionHeader("Action Plan", [16, 185, 129])
            data.actionPlan.forEach((action, index) => {
                addText(`${index + 1}. ${action}`, 10, false)
            })
        }

        // Transcript
        if (data.transcript.length > 0) {
            addSectionHeader("Transcript", [107, 114, 128])
            data.transcript.forEach((segment, index) => {
                if (yPosition > pageHeight - margin - 20) {
                    doc.addPage()
                    yPosition = margin
                }
                doc.setFont("helvetica", "bold")
                doc.setFontSize(9)
                doc.setTextColor(100, 100, 100)
                doc.text(`[${segment.time}]`, margin, yPosition)
                yPosition += 5

                doc.setFont("helvetica", "normal")
                doc.setFontSize(10)
                doc.setTextColor(0, 0, 0)
                const lines = doc.splitTextToSize(segment.text, maxWidth)
                lines.forEach(line => {
                    if (yPosition > pageHeight - margin) {
                        doc.addPage()
                        yPosition = margin
                    }
                    doc.text(line, margin, yPosition)
                    yPosition += 5
                })
                yPosition += 3
            })
        }

        // Footer on last page
        const totalPages = doc.internal.pages.length - 1
        for (let i = 1; i <= totalPages; i++) {
            doc.setPage(i)
            doc.setFontSize(8)
            doc.setTextColor(150, 150, 150)
            doc.text(`Page ${i} of ${totalPages}`, pageWidth / 2, pageHeight - 10, { align: 'center' })
            doc.text(`Generated by TalkSense AI on ${new Date().toLocaleString()}`, margin, pageHeight - 10)
        }

        // Save the PDF
        const fileName = `TalkSense_${modeLabel.replace(' ', '_')}_${new Date().toISOString().split('T')[0]}.pdf`
        doc.save(fileName)
    }

    // Share Handler
    const handleShare = async () => {
        const shareData = {
            title: `TalkSense AI - ${modeLabel} Analysis`,
            text: `${data.summary}\n\nSentiment: ${data.sentimentLabel}\nDuration: ${data.duration}`,
            url: window.location.href
        }

        try {
            if (navigator.share) {
                await navigator.share(shareData)
            } else {
                // Fallback: Copy to clipboard
                const textToCopy = `${shareData.title}\n\n${shareData.text}\n\n${shareData.url}`
                await navigator.clipboard.writeText(textToCopy)
                alert('Analysis details copied to clipboard!')
            }
        } catch (err) {
            if (err.name !== 'AbortError') {
                console.error('Error sharing:', err)
                // Fallback: Copy to clipboard
                try {
                    const textToCopy = `${shareData.title}\n\n${shareData.text}\n\n${shareData.url}`
                    await navigator.clipboard.writeText(textToCopy)
                    alert('Analysis details copied to clipboard!')
                } catch (clipErr) {
                    console.error('Clipboard error:', clipErr)
                    alert('Unable to share. Please try again.')
                }
            }
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center animate-fade-in">
                <div className="text-center">
                    <div className="w-20 h-20 mx-auto mb-6 relative">
                        <svg className="animate-spin text-indigo-600" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-3 h-3 bg-indigo-600 rounded-full animate-pulse-subtle"></div>
                        </div>
                    </div>
                    <p className="text-gray-900 font-semibold text-lg mb-2">Preparing your analysis</p>
                    <p className="text-gray-500 text-sm">This will only take a moment...</p>
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

            <div className="max-w-7xl mx-auto px-6 py-8 animate-fade-in">

                {/* Header & Meta */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                            Analysis Results
                        </h1>
                        <p className="text-gray-500 mt-1 flex items-center gap-2">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                            </span>
                            Processed on {new Date().toLocaleString('en-IN', {
                                day: 'numeric',
                                month: 'short',
                                year: 'numeric',
                                hour: 'numeric',
                                minute: '2-digit',
                                hour12: true,
                                timeZone: 'Asia/Kolkata'
                            })} IST • Duration: {data.duration || "00:00"}
                        </p>
                    </div>

                    {/* Status Badges Section */}
                    <div className="flex items-center gap-3">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border ${modeColor}`}>
                            <span className={`w-2 h-2 rounded-full ${modeDot}`}></span>
                            {modeLabel}
                        </span>
                        <SentimentBadge score={data.sentimentScore} label={data.sentimentLabel} />
                    </div>
                </div>

                {/* Two Column Layout */}
                <div className="grid lg:grid-cols-2 gap-8">

                    {/* LEFT COLUMN - Summary, Insights, Actions */}
                    <div className="space-y-6 animate-slide-up">

                        {/* Summary Section */}
                        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-smooth">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                Executive Summary
                            </h2>
                            <p className="text-gray-600 leading-relaxed mb-4">
                                {data.summary}
                            </p>

                            {/* NEW: Display both Meeting Quality and Project Risk */}
                            <div className="border-t border-gray-100 pt-3 space-y-2">
                                {data.meetingQuality && (
                                    <div className="text-sm text-gray-500 font-medium flex items-center gap-2">
                                        <span>Meeting Quality:</span>
                                        <span className={`px-2 py-0.5 rounded text-xs tracking-wide font-semibold ${data.meetingQuality.label === "High" ? "bg-green-100 text-green-700" :
                                            data.meetingQuality.label === "Low" ? "bg-red-100 text-red-700" :
                                                "bg-yellow-100 text-yellow-700"
                                            }`}>
                                            {data.meetingQuality.label}
                                        </span>
                                    </div>
                                )}
                                {data.projectRisk && data.projectRisk.label !== "Low" && (
                                    <div className="text-sm text-gray-500 font-medium flex items-center gap-2">
                                        <span>Project Risk:</span>
                                        <span className={`px-2 py-0.5 rounded text-xs tracking-wide font-semibold ${data.projectRisk.label === "High" ? "bg-red-100 text-red-700" :
                                            data.projectRisk.label === "Medium" ? "bg-orange-100 text-orange-700" :
                                                "bg-green-100 text-green-700"
                                            }`}>
                                            {data.projectRisk.label}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Key Insights */}
                        {data.keyInsights.length > 0 && (
                            <div>
                                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                    <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                    Key Insights
                                </h2>
                                <div className="space-y-3">
                                    {data.keyInsights.map((item, i) => (
                                        <div key={i} className="animate-slide-up" style={{ animationDelay: `${i * 50}ms` }}>
                                            <InsightCard text={item.text} type={item.type} />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Action Plan */}
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
                                                <span className="text-gray-700 text-sm">{item}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* RIGHT COLUMN - Transcript */}
                    <div className="space-y-4 animate-slide-up stagger-1">
                        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                            <div className="bg-gray-50/80 px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                                    <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                                    </svg>
                                    Transcript
                                </h2>
                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    {data.transcript.length} segments
                                </span>
                            </div>
                            <div className="divide-y divide-gray-50 p-2 max-h-[600px] overflow-y-auto">
                                {data.transcript.map((segment, i) => (
                                    <TranscriptBlock key={i} segment={segment} />
                                ))}
                            </div>
                        </div>

                        {/* Export & Share Buttons */}
                        <div className="flex gap-3">
                            <button onClick={handleExportPDF} className="flex-1 btn-primary group">
                                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                Export PDF
                            </button>
                            <button onClick={handleShare} className="flex-1 btn-secondary group">
                                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                                </svg>
                                Share
                            </button>
                        </div>
                    </div>

                </div>

            </div>
        </div>
    )
}
