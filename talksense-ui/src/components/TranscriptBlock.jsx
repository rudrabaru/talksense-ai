export default function TranscriptBlock({ segment }) {
    return (
        <div className="border-b py-3">
            <div className="text-xs text-gray-400 mb-1">
                {segment.time}
            </div>
            <p className="text-gray-700">
                {segment.text}
            </p>
        </div>
    )
}