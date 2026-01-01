export default function InsightCard({ text, type }) {
    // Visual mapping for types
    const styles = {
        "Escalation Required": "bg-red-500 ring-red-100",
        "Execution Risk": "bg-amber-500 ring-amber-100",
        "Decision Ambiguity": "bg-gray-400 ring-gray-100",
        "Ownership Gap": "bg-gray-400 ring-gray-100",
        "Positive Momentum": "bg-green-500 ring-green-100"
    }

    // Default style if type not found
    const indicatorStyle = styles[type] || "bg-indigo-500 ring-indigo-100"

    return (
        <div className="bg-white border border-gray-100 p-5 rounded-xl shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-1 h-full flex flex-col group">
            {/* Subtitle for the type */}
            {type && (
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                    {type}
                </span>
            )}
            <div className="flex items-start gap-3">
                <div className="mt-1 min-w-5">
                    <div className={`w-2 h-2 rounded-full ring-4 transition-all group-hover:ring-opacity-50 ${indicatorStyle}`}></div>
                </div>
                <p className="text-gray-700 font-medium leading-relaxed">
                    {text}
                </p>
            </div>
        </div>
    )
}