import data from "../mock/analysis.json"
import SentimentBadge from "../components/SentimentBadge"
import InsightCard from "../components/InsightCard"
import TranscriptBlock from "../components/TranscriptBlock"
import { Link } from "react-router-dom"

export default function ResultsPage() {
    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-4xl mx-auto space-y-6">

                <div className="bg-white p-6 rounded-xl shadow">
                    <h2 className="text-2xl font-bold mb-2">
                        Analysis Summary
                    </h2>
                    <p className="text-gray-600 mb-4">
                        {data.summary}
                    </p>
                    <SentimentBadge score={data.sentimentScore} />
                </div>

                <div className="bg-white p-6 rounded-xl shadow">
                    <h3 className="font-semibold mb-3">
                        Key Insights
                    </h3>
                    <div className="space-y-2">
                        {data.insights.map((item, i) => (
                            <InsightCard key={i} text={item} />
                        ))}
                    </div>
                </div>

                <div className="bg-white p-6 rounded-xl shadow">
                    <h3 className="font-semibold mb-3">
                        Conversation Transcript
                    </h3>
                    {data.transcript.map((segment, i) => (
                        <TranscriptBlock key={i} segment={segment} />
                    ))}
                </div>

                <Link
                    to="/"
                    className="text-indigo-600 underline block text-center"
                >
                    Analyze another conversation
                </Link>

            </div>
        </div>
    )
}