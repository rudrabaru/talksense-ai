import { BrowserRouter, Routes, Route } from "react-router-dom"
import HomePage from "./pages/HomePage"
import UploadPage from "./pages/UploadPage"
import ResultsPage from "./pages/ResultsPage"
import DashboardPage from "./pages/DashboardPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/dashboard/:sessionId" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  )
}