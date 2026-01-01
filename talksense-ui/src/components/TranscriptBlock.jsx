export default function TranscriptBlock({ segment }) {
    if (!segment) return null

    const sentiment = segment.sentiment ?? 0 // Default to 0 if undefined
    const displayTime = segment.time || "00:00"
    const displayText = segment.text || ""

    const sentimentColor =
        sentiment >= 0.2 ? "border-green-500 bg-green-50" :
            sentiment <= -0.2 ? "border-red-500 bg-red-50" :
                "border-transparent hover:bg-gray-50"

    return (
        <div className={`border-b border-l-4 py-3 px-4 ${sentimentColor} transition-colors`}>
            <div className="flex justify-between items-baseline mb-1">
                <span className="text-xs text-gray-400 font-medium">
                    {displayTime}
                </span>
                <span className="text-xs text-gray-400">
                    {sentiment >= 0.2 ? "Positive" : sentiment <= -0.2 ? "Negative" : "Neutral"}
                </span>
            </div>
            <p className="text-gray-700 leading-relaxed">
                {displayText}
            </p>
        </div>
    )
}