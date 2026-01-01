export default function ModeSelector({ mode, setMode }) {
    return (
        <div className="flex bg-gray-100 p-1 rounded-xl w-full">
            {["meeting", "sales"].map((type) => (
                <button
                    key={type}
                    onClick={() => setMode(type)}
                    className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 capitalize ${mode === type
                        ? "bg-white text-indigo-600 shadow-sm scale-[1.02]"
                        : "text-gray-500 hover:text-gray-700"
                        }`}
                >
                    {type} Mode
                </button>
            ))}
        </div>
    )
}