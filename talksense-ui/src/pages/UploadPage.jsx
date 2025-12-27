import { useState } from "react"
import { useNavigate } from "react-router-dom"
import ModeSelector from "../components/ModeSelector"

export default function UploadPage() {
    const navigate = useNavigate()
    const [mode, setMode] = useState("meeting")

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="bg-white shadow-md rounded-xl p-8 w-full max-w-md">
                <h1 className="text-2xl font-bold text-center mb-6">
                    TalkSense AI
                </h1>

                <input
                    type="file"
                    className="w-full mb-4 border rounded-lg p-2"
                />

                <ModeSelector mode={mode} setMode={setMode} />

                <button
                    onClick={() => navigate("/results")}
                    className="w-full mt-6 bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 transition"
                >
                    Analyze Conversation
                </button>
            </div>
        </div>
    )
}