export default function SentimentBadge({ score }) {
    const label =
        score > 0.2 ? "Positive" :
            score < -0.2 ? "Negative" :
                "Neutral"

    const color =
        score > 0.2 ? "bg-green-100 text-green-700" :
            score < -0.2 ? "bg-red-100 text-red-700" :
                "bg-gray-100 text-gray-700"

    return (
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${color}`}>
            Sentiment: {label}
        </span>
    )
}