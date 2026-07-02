import { Link } from "react-router-dom"

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-neutral-950 text-white">
      <h1 className="text-6xl font-bold mb-4">404</h1>
      <p className="text-xl text-neutral-400 mb-8">Page Not Found</p>
      <Link
        to="/"
        className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium transition-colors"
      >
        Return Home
      </Link>
    </div>
  )
}
