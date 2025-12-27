export default function TranscriptBlock({ segment }) {
    const sentimentColor =
        segment.sentiment >= 0.2 ? "border-green-500 bg-green-50" :
            segment.sentiment <= -0.2 ? "border-red-500 bg-red-50" :
                "border-transparent hover:bg-gray-50"

    return (
        <div className={`border-b border-l-4 py-3 px-4 ${sentimentColor} transition-colors`}>
            <div className="flex justify-between items-baseline mb-1">
                <span className="text-xs text-gray-400 font-medium">
                    {segment.time}
                </span>
                <span className="text-xs text-gray-400">
                    {segment.sentiment >= 0.2 ? "Positive" : segment.sentiment <= -0.2 ? "Negative" : "Neutral"}
                </span>
            </div>
            <p className="text-gray-700 leading-relaxed">
                {segment.text}
            </p>
        </div>
    )
}