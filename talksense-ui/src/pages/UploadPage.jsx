import { useState } from "react"
import { useNavigate } from "react-router-dom"
import ModeSelector from "../components/ModeSelector"

export default function UploadPage() {
    const navigate = useNavigate()
    const [mode, setMode] = useState("meeting")
    const [file, setFile] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
            setError(null)
        }
    }

    const handleAnalyze = async () => {
        if (!file) {
            setError("Please select an audio file first.")
            return
        }

        setLoading(true)
        setError(null)

        const formData = new FormData()
        formData.append("file", file)

        try {
            // Note: Ensure your backend is running on port 8000
            const response = await fetch(`http://127.0.0.1:8000/analyze?mode=${mode}`, {
                method: "POST",
                body: formData,
            })

            if (!response.ok) {
                throw new Error("Analysis failed. Please try again.")
            }

            const data = await response.json()
            navigate("/results", { state: { data, mode } })
        } catch (err) {
            console.error(err)
            setError("Failed to connect. Is the backend running on port 8000?")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-purple-50 p-6 relative">
            <button
                onClick={() => navigate("/")}
                className="absolute top-6 left-6 flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors bg-white/50 px-3 py-2 rounded-lg backdrop-blur-sm border border-transparent hover:border-indigo-100 hover:shadow-sm"
            >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Home
            </button>

            <div className={`bg-white/80 backdrop-blur-xl shadow-xl rounded-2xl p-8 w-full max-w-lg border border-white/50 transition-opacity ${loading ? "opacity-50 pointer-events-none" : ""}`}>
                <div className="text-center mb-10">
                    <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600 tracking-tight mb-2">
                        TalkSense AI
                    </h1>
                    <p className="text-gray-500 font-medium">
                        Transform conversations into actionable intelligence
                    </p>
                </div>

                <div className="space-y-6">
                    {/* Upload Area */}
                    <div>
                        <label className={`block w-full cursor-pointer group ${file ? "border-indigo-500" : ""}`}>
                            <div className={`border-2 border-dashed ${file ? "border-indigo-500 bg-indigo-50" : "border-gray-300 bg-gray-50"} rounded-xl p-10 flex flex-col items-center justify-center transition-all group-hover:bg-indigo-50/50 group-hover:border-indigo-400`}>
                                <div className="p-4 bg-white rounded-full shadow-sm mb-4 group-hover:shadow-md transition-shadow">
                                    <svg className="w-8 h-8 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                </div>
                                <span className="text-gray-900 font-semibold mb-1">
                                    {file ? file.name : "Click to upload audio"}
                                </span>
                                <span className="text-sm text-gray-400">
                                    {file ? "Ready to analyze" : "MP3, WAV or M4A (max 50MB)"}
                                </span>
                            </div>
                            <input type="file" className="hidden" accept="audio/*" onChange={handleFileChange} />
                        </label>
                        {error && <p className="text-red-500 text-sm text-center mt-2">{error}</p>}
                    </div>

                    {/* Context Selection */}
                    <div className="space-y-3">
                        <label className="text-sm font-semibold text-gray-700 ml-1">
                            Conversation Context
                        </label>
                        <ModeSelector mode={mode} setMode={setMode} />
                    </div>

                    {/* Action Buttons */}
                    <div className="space-y-3">
                        <button
                            onClick={handleAnalyze}
                            disabled={loading}
                            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-indigo-200 hover:shadow-indigo-300 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-70 disabled:cursor-not-allowed flex justify-center items-center"
                        >
                            {loading ? (
                                <>
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Processing...
                                </>
                            ) : (
                                "Analyze Conversation"
                            )}
                        </button>

                        <button
                            onClick={() => {
                                import("../mock/analysis.json").then((mod) => {
                                    navigate("/results", { state: { data: mod.default, mode } })
                                })
                            }}
                            className="w-full bg-white text-indigo-600 font-bold py-3.5 rounded-xl border border-indigo-200 shadow-sm hover:bg-indigo-50 hover:border-indigo-300 transition-all duration-200 flex justify-center items-center"
                        >
                            Try with Demo Data
                        </button>
                    </div>

                    <p className="text-center text-xs text-gray-400 mt-4">
                        Securely processed • Enterprise grade privacy
                    </p>
                </div>
            </div>
        </div>
    )
}