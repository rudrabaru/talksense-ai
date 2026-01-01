export default function SentimentBadge({ score, label }) {
    // Logic: Use explicit label if available, else derive from score
    let displayLabel = "Neutral"
    let color = "bg-gray-100 text-gray-700"

    if (label) {
        displayLabel = label.charAt(0).toUpperCase() + label.slice(1) // Capitalize
        const lowerLabel = label.toLowerCase()
        if (lowerLabel.includes("positive")) {
            color = "bg-green-100 text-green-700"
        } else if (lowerLabel.includes("negative")) {
            color = "bg-red-100 text-red-700"
        } else if (lowerLabel.includes("mixed")) {
            color = "bg-amber-100 text-amber-700"
        }
    } else {
        // Fallback: Score-based (Kept for backward compat or if label missing)
        if (score > 0.2) {
            displayLabel = "Positive"
            color = "bg-green-100 text-green-700"
        } else if (score < -0.2) {
            displayLabel = "Negative"
            color = "bg-red-100 text-red-700"
        }
    }

    return (
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${color}`}>
            Sentiment: {displayLabel}
        </span>
    )
}