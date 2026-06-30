import { BrowserRouter, Routes, Route } from "react-router-dom"
import HomePage from "./pages/HomePage"
import UploadPage from "./pages/UploadPage"
import ResultsPage from "./pages/ResultsPage"
import DashboardPage from "./pages/DashboardPage"
import SessionsPage from "./pages/SessionsPage"
import ComparisonPage from "./pages/ComparisonPage"
import SystemAudioTester from "./pages/SystemAudioTester"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/dashboard/:sessionId" element={<DashboardPage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/compare" element={<ComparisonPage />} />
        <Route path="/test-system-audio" element={<SystemAudioTester />} />
      </Routes>
    </BrowserRouter>
  )
}
