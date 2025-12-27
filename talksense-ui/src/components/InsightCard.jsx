export default function InsightCard({ text }) {
    return (
        <div className="bg-white border border-gray-100 p-5 rounded-xl shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-1 h-full flex flex-col group">
            <div className="flex items-start gap-3">
                <div className="mt-1 min-w-5">
                    <div className="w-2 h-2 rounded-full bg-amber-400 ring-4 ring-amber-50 group-hover:ring-amber-100 transition-all"></div>
                </div>
                <p className="text-gray-700 font-medium leading-relaxed">
                    {text}
                </p>
            </div>
        </div>
    )
}