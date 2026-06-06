import { BrowserRouter, Routes, Route } from "react-router-dom"
import HomePage from "./pages/HomePage"
import UploadPage from "./pages/UploadPage"
import ResultsPage from "./pages/ResultsPage"
import TranscriptLive from "./components/TranscriptLive"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<TranscriptLive />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/live" element={<TranscriptLive />} />
      </Routes>
    </BrowserRouter>
  )
}