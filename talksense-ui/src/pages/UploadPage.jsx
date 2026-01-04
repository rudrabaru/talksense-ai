import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { analyzeAudio, loadDemoData } from "../services/api"
import logoImage from "../assets/logo/logo.png"

export default function UploadPage() {
    const navigate = useNavigate()
    const [mode, setMode] = useState("meeting")
    const [file, setFile] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [progress, setProgress] = useState("")
    const [success, setSuccess] = useState(false)

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0]

            // File size validation (50MB max)
            const maxSize = 50 * 1024 * 1024 // 50MB in bytes
            if (selectedFile.size > maxSize) {
                setError(`File size exceeds 50MB limit. Please select a smaller file.`)
                setFile(null)
                return
            }

            setFile(selectedFile)
            setError(null)
            setSuccess(false)
        }
    }

    const handleAnalyze = async () => {
        if (!file) {
            setError("Please select an audio file first.")
            return
        }

        setLoading(true)
        setError(null)
        setProgress("Uploading file...")

        try {
            // Simulate upload progress
            setTimeout(() => setProgress("Transcribing audio..."), 800)
            setTimeout(() => setProgress("Analyzing sentiment..."), 2000)
            setTimeout(() => setProgress("Extracting insights..."), 3500)

            const result = await analyzeAudio(file, mode)

            setProgress("Complete!")
            setSuccess(true)

            // Smooth transition to results
            setTimeout(() => {
                navigate('/results', {
                    state: {
                        analysisData: result,
                        fromUpload: true
                    }
                })
            }, 800)

        } catch (err) {
            const errorMessage = err.message || "Analysis failed"
            setError(`${errorMessage}. Please check your connection and try again.`)
            setLoading(false)
            setProgress("")
        }
    }

    const handleDemoData = async () => {
        setLoading(true)
        setError(null)
        setProgress("Loading demo data...")

        try {
            const result = await loadDemoData(mode)

            setProgress("Complete!")
            setSuccess(true)

            // Navigate to results with demo data
            setTimeout(() => {
                navigate('/results', {
                    state: {
                        analysisData: result,
                        isDemo: true
                    }
                })
            }, 600)

        } catch (err) {
            setError("Failed to load demo data. Please try again.")
            setLoading(false)
            setProgress("")
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-indigo-50/20">
            {/* Navbar */}
            <nav className="border-b border-gray-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
                <div className="mx-auto px-6 lg:px-12 xl:px-16 h-16 flex items-center justify-between">
                    <button
                        onClick={() => navigate('/')}
                        className="flex items-center gap-3 hover:opacity-80 transition-opacity"
                    >
                        <div className="relative w-9 h-9">
                            <img src={logoImage} alt="TalkSense AI Logo" className="w-full h-full object-contain" />
                        </div>
                        <span className="font-bold text-xl tracking-tight">
                            <span style={{ color: '#4F46E5' }}>TalkSense</span>
                            <span style={{ color: '#14B8A6' }}> AI</span>
                        </span>
                    </button>
                    <button
                        onClick={() => navigate('/')}
                        className="text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors"
                    >
                        ← Back to Home
                    </button>
                </div>
            </nav>

            {/* Main Content - Full Width Layout */}
            <div className="mx-auto px-6 lg:px-12 xl:px-16 py-12 lg:py-20">
                <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center max-w-7xl mx-auto">

                    {/* Left Column - Info */}
                    <div className="lg:pr-8 animate-slide-up">

                        <h1 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-6 tracking-tight">
                            Upload your conversation
                        </h1>

                        <p className="text-lg text-gray-600 mb-8 leading-relaxed">
                            Select an audio file and choose the conversation context. Our AI will analyze the content and extract actionable insights in seconds.
                        </p>

                        <div className="space-y-6">
                            <div className="flex items-start gap-4 p-4 bg-white rounded-xl border border-gray-200 hover-lift">
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

                            <div className="flex items-start gap-4 p-4 bg-white rounded-xl border border-gray-200 hover-lift">
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
                    <div className={`relative bg-white rounded-2xl shadow-xl border border-gray-200 p-8 lg:p-10 transition-smooth animate-slide-up ${loading ? "opacity-90" : ""}`}>

                        {/* Loading Progress Overlay */}
                        {loading && (
                            <div className="absolute inset-0 bg-white/95 backdrop-blur-sm rounded-2xl flex flex-col items-center justify-center z-10 animate-fade-in">
                                <div className="w-16 h-16 mb-4">
                                    <svg className="animate-spin text-indigo-600" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                </div>
                                <p className="text-lg font-semibold text-gray-900 mb-2 animate-pulse-subtle">{progress}</p>
                                <div className="w-48 h-1 bg-gray-200 rounded-full overflow-hidden">
                                    <div className="h-full bg-indigo-600 animate-shimmer"></div>
                                </div>
                                {success && (
                                    <div className="mt-4 flex items-center gap-2 text-teal-600 animate-scale-in">
                                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                        <span className="font-medium">Success!</span>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Upload Area */}
                        <div className="mb-8">
                            <label className="block text-sm font-semibold text-gray-900 mb-3">
                                Audio File
                            </label>
                            <label className={`block w-full cursor-pointer group transition-smooth ${file ? "border-indigo-500" : ""}`}>
                                <div className={`border-2 border-dashed ${file ? "border-indigo-500 bg-indigo-50" : "border-gray-300 bg-gray-50"} rounded-xl p-12 flex flex-col items-center justify-center transition-smooth group-hover:bg-indigo-50/50 group-hover:border-indigo-400 ${file ? 'animate-scale-in' : ''}`}>
                                    <div className={`w-16 h-16 rounded-full bg-white shadow-sm mb-4 flex items-center justify-center transition-smooth group-hover:shadow-md group-hover:scale-110 ${file ? 'bg-indigo-100' : ''}`}>
                                        {file ? (
                                            <svg className="w-8 h-8 text-indigo-600 animate-scale-in" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                        ) : (
                                            <svg className="w-8 h-8 text-gray-400 group-hover:text-indigo-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
                                <input type="file" className="hidden" accept="audio/*" onChange={handleFileChange} disabled={loading} />
                            </label>
                            {error && (
                                <div className="mt-3 text-sm text-red-600 flex items-center gap-2 animate-slide-down">
                                    <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
                                    disabled={loading}
                                    className={`p-4 rounded-xl border-2 text-left transition-smooth hover-lift ${mode === "meeting"
                                        ? "border-indigo-500 bg-indigo-50 shadow-sm"
                                        : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
                                        } disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:transform-none`}
                                >
                                    <div className="font-semibold text-gray-900 mb-1">Meeting</div>
                                    <div className="text-sm text-gray-600">Team discussions & decisions</div>
                                </button>
                                <button
                                    onClick={() => setMode("sales")}
                                    disabled={loading}
                                    className={`p-4 rounded-xl border-2 text-left transition-smooth hover-lift ${mode === "sales"
                                        ? "border-teal-500 bg-teal-50 shadow-sm"
                                        : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
                                        } disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:transform-none`}
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
                                className="w-full bg-indigo-600 text-white font-semibold py-4 rounded-xl shadow-lg hover:bg-indigo-700 hover:shadow-xl transition-smooth disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center hover-lift disabled:hover:transform-none active:scale-95"
                            >
                                {loading && !success ? (
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
                                onClick={handleDemoData}
                                disabled={loading}
                                className="w-full bg-white text-gray-700 font-semibold py-4 rounded-xl border-2 border-gray-200 hover:bg-gray-50 hover:border-gray-300 transition-smooth hover-lift disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:transform-none active:scale-95"
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