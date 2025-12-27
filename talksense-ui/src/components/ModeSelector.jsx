export default function ModeSelector({ mode, setMode }) {
    return (
        <div className="flex gap-4 justify-center mt-4">
            {["meeting", "sales"].map((type) => (
                <button
                    key={type}
                    onClick={() => setMode(type)}
                    className={`px-4 py-2 rounded-lg border ${mode === type
                            ? "bg-indigo-600 text-white"
                            : "bg-white text-gray-700"
                        }`}
                >
                    {type === "meeting" ? "Meeting" : "Sales"}
                </button>
            ))}
        </div>
    )
}