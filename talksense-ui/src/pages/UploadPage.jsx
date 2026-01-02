import { useState } from "react"

export default function UploadPage() {
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
        setTimeout(() => {
            setLoading(false)
            alert("In production, this would navigate to results page")
        }, 2000)
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-indigo-50/20">
            {/* Navbar */}
            <nav className="border-b border-gray-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
                <div className="mx-auto px-6 lg:px-12 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="relative w-9 h-9">
                            <svg viewBox="0 0 36 36" className="w-full h-full">
                                <rect x="2" y="2" width="32" height="32" rx="8" fill="#4F46E5"/>
                                <path d="M12 18h2v-4h-2v4zm4 0h2v-8h-2v8zm4 0h2v-6h-2v6zm4 0h2v-10h-2v10z" fill="white" opacity="0.9"/>
                                <path d="M10 22c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2" stroke="white" strokeWidth="1.5" fill="none" opacity="0.7"/>
                            </svg>
                        </div>
                        <span className="font-bold text-xl tracking-tight text-gray-900">TalkSense</span>
                    </div>
                    <button className="text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors">
                        ← Back to Home
                    </button>
                </div>
            </nav>

            {/* Main Content - Full Width Layout */}
            <div className="mx-auto px-6 lg:px-12 xl:px-16 py-12 lg:py-20">
                <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center max-w-7xl mx-auto">
                    
                    {/* Left Column - Info */}
                    <div className="lg:pr-8">
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 text-indigo-700 text-sm font-medium mb-6 border border-indigo-100">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                            </span>
                            Step 1 of 3
                        </div>

                        <h1 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-6 tracking-tight">
                            Upload your conversation
                        </h1>

                        <p className="text-lg text-gray-600 mb-8 leading-relaxed">
                            Select an audio file and choose the conversation context. Our AI will analyze the content and extract actionable insights in seconds.
                        </p>

                        <div className="space-y-6">
                            <div className="flex items-start gap-4 p-4 bg-white rounded-xl border border-gray-200">
                                <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                                    <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                    </svg>
                                </div>
                                <div>
                                    <div className="font-semibold text-gray-900 mb-1">Enterprise Security</div>
                                    <div className="text-sm text-gray-600">End-to-end encryption. Your data never leaves your control.</div>
                                </div>
                            </div>

                            <div className="flex items-start gap-4 p-4 bg-white rounded-xl border border-gray-200">
                                <div className="w-10 h-10 rounded-lg bg-teal-50 flex items-center justify-center flex-shrink-0">
                                    <svg className="w-5 h-5 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                </div>
                                <div>
                                    <div className="font-semibold text-gray-900 mb-1">Fast Processing</div>
                                    <div className="text-sm text-gray-600">Analysis completes in under 60 seconds for most recordings.</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right Column - Upload Form */}
                    <div className={`bg-white rounded-2xl shadow-xl border border-gray-200 p-8 lg:p-10 transition-opacity ${loading ? "opacity-50 pointer-events-none" : ""}`}>
                        
                        {/* Upload Area */}
                        <div className="mb-8">
                            <label className="block text-sm font-semibold text-gray-900 mb-3">
                                Audio File
                            </label>
                            <label className={`block w-full cursor-pointer group ${file ? "border-indigo-500" : ""}`}>
                                <div className={`border-2 border-dashed ${file ? "border-indigo-500 bg-indigo-50" : "border-gray-300 bg-gray-50"} rounded-xl p-12 flex flex-col items-center justify-center transition-all group-hover:bg-indigo-50/50 group-hover:border-indigo-400`}>
                                    <div className="w-16 h-16 rounded-full bg-white shadow-sm mb-4 flex items-center justify-center group-hover:shadow-md transition-shadow">
                                        {file ? (
                                            <svg className="w-8 h-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                        ) : (
                                            <svg className="w-8 h-8 text-gray-400 group-hover:text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                            </svg>
                                        )}
                                    </div>
                                    <span className="text-gray-900 font-semibold mb-2">
                                        {file ? file.name : "Click to upload"}
                                    </span>
                                    <span className="text-sm text-gray-500">
                                        {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "MP3, WAV, M4A (max 50MB)"}
                                    </span>
                                </div>
                                <input type="file" className="hidden" accept="audio/*" onChange={handleFileChange} />
                            </label>
                            {error && (
                                <div className="mt-3 text-sm text-red-600 flex items-center gap-2">
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    {error}
                                </div>
                            )}
                        </div>

                        {/* Mode Selector */}
                        <div className="mb-8">
                            <label className="block text-sm font-semibold text-gray-900 mb-3">
                                Conversation Type
                            </label>
                            <div className="grid grid-cols-2 gap-4">
                                <button
                                    onClick={() => setMode("meeting")}
                                    className={`p-4 rounded-xl border-2 text-left transition-all ${
                                        mode === "meeting"
                                            ? "border-indigo-500 bg-indigo-50"
                                            : "border-gray-200 bg-white hover:border-gray-300"
                                    }`}
                                >
                                    <div className="font-semibold text-gray-900 mb-1">Meeting</div>
                                    <div className="text-sm text-gray-600">Team discussions & decisions</div>
                                </button>
                                <button
                                    onClick={() => setMode("sales")}
                                    className={`p-4 rounded-xl border-2 text-left transition-all ${
                                        mode === "sales"
                                            ? "border-teal-500 bg-teal-50"
                                            : "border-gray-200 bg-white hover:border-gray-300"
                                    }`}
                                >
                                    <div className="font-semibold text-gray-900 mb-1">Sales Call</div>
                                    <div className="text-sm text-gray-600">Client conversations</div>
                                </button>
                            </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="space-y-3">
                            <button
                                onClick={handleAnalyze}
                                disabled={loading || !file}
                                className="w-full bg-indigo-600 text-white font-semibold py-4 rounded-xl shadow-lg hover:bg-indigo-700 hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center"
                            >
                                {loading ? (
                                    <>
                                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Analyzing...
                                    </>
                                ) : (
                                    "Start Analysis"
                                )}
                            </button>

                            <button
                                onClick={() => alert("Loading demo data...")}
                                className="w-full bg-white text-gray-700 font-semibold py-4 rounded-xl border-2 border-gray-200 hover:bg-gray-50 hover:border-gray-300 transition-all"
                            >
                                Try with Demo Data
                            </button>
                        </div>

                        <p className="text-center text-xs text-gray-500 mt-6">
                            Processing happens securely • No data retention without consent
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}