import { Link } from "react-router-dom"

export default function HomePage() {
    return (
        <div className="min-h-screen bg-white">
            {/* Navbar */}
            <nav className="border-b border-gray-100 bg-white/80 backdrop-blur-md sticky top-0 z-50">
                <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold shadow-md shadow-indigo-100">
                            T
                        </div>
                        <span className="font-bold text-xl tracking-tight text-gray-900">TalkSense</span>
                    </div>
                    <div className="hidden md:flex gap-8 text-sm font-medium text-gray-500">
                        <a href="#how-it-works" className="hover:text-gray-900 transition-colors">How it Works</a>
                        <a href="#solutions" className="hover:text-gray-900 transition-colors">Solutions</a>
                    </div>
                    <div>
                        <Link
                            to="/upload"
                            className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-all shadow-sm hover:shadow"
                        >
                            Try TalkSense
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <header className="relative pt-20 pb-32 overflow-hidden">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-indigo-50/50 rounded-full blur-3xl -z-10 opacity-60"></div>

                <div className="max-w-4xl mx-auto px-6 text-center">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-sm font-medium mb-8 border border-indigo-100">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                        </span>
                        Introducing Conversation Intelligence V1
                    </div>

                    <h1 className="text-5xl md:text-6xl font-bold text-gray-900 tracking-tight mb-6 leading-[1.1]">
                        Turn conversations into <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-violet-600">clarity and action.</span>
                    </h1>

                    <p className="text-xl text-gray-500 mb-10 max-w-2xl mx-auto leading-relaxed">
                        TalkSense analyzes your most important discussions to extract decisions, sentiment shifts, and hidden risks. Move from noise to understanding in seconds.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            to="/upload"
                            className="w-full sm:w-auto px-8 py-3.5 bg-gray-900 text-white font-medium rounded-xl hover:bg-gray-800 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5 flex items-center justify-center gap-2"
                        >
                            Analyze a Conversation
                            <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        </Link>
                        <button className="w-full sm:w-auto px-8 py-3.5 bg-white text-gray-600 font-medium rounded-xl border border-gray-200 hover:bg-gray-50 transition-colors">
                            View Sample Report
                        </button>
                    </div>
                </div>
            </header>

            {/* How it Works (Micro-workflow) */}
            <section id="how-it-works" className="py-20 bg-gray-50 border-y border-gray-100">
                <div className="max-w-6xl mx-auto px-6">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold text-gray-900 mb-4">How it works</h2>
                        <p className="text-gray-500">A simple workflow designed for busy professionals.</p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8">
                        {[
                            {
                                step: "01",
                                title: "Upload Audio",
                                desc: "Securely upload your meeting recording or sales call. We support offline-first processing for privacy.",
                                icon: (
                                    <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                )
                            },
                            {
                                step: "02",
                                title: "AI Analysis",
                                desc: "Our engine detects sentiment, extracts decisions, and identifies key friction points automatically.",
                                icon: (
                                    <svg className="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                    </svg>
                                )
                            },
                            {
                                step: "03",
                                title: "Act on Insights",
                                desc: "Get a structured summary, action items with owners, and objection handling tips instantly.",
                                icon: (
                                    <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                )
                            }
                        ].map((item, i) => (
                            <div key={i} className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-4 opacity-5 font-black text-6xl text-gray-900 select-none group-hover:opacity-10 transition-opacity">
                                    {item.step}
                                </div>
                                <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                                    {item.icon}
                                </div>
                                <h3 className="text-xl font-bold text-gray-900 mb-3">{item.title}</h3>
                                <p className="text-gray-500 leading-relaxed">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Features / Solutions */}
            <section id="solutions" className="py-24 bg-white">
                <div className="max-w-6xl mx-auto px-6">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold text-gray-900 mb-4">Two modes. One purpose.</h2>
                        <p className="text-gray-500">Optimized intelligence for the conversations that define your business.</p>
                    </div>

                    <div className="grid md:grid-cols-2 gap-12">
                        {/* Meeting Mode Card */}
                        <div className="flex flex-col h-full bg-gradient-to-b from-blue-50/50 to-white rounded-3xl border border-blue-100 p-8 md:p-10 overflow-hidden relative">
                            <div className="relative z-10">
                                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-xs font-bold uppercase tracking-wider mb-6">
                                    Meeting Mode
                                </div>
                                <h3 className="text-3xl font-bold text-gray-900 mb-4">Align your team.</h3>
                                <p className="text-gray-600 mb-8 leading-relaxed">
                                    Stop wondering what was decided. TalkSense captures key decisions, maps action items to owners, and flags unresolved tension so you can follow up with confidence.
                                </p>
                                <ul className="space-y-3 mb-8">
                                    {[
                                        "Automated Executive Summaries",
                                        "Action Item & Deadline Extraction",
                                        "Decision Tracking",
                                        "Tension & Blocker Detection"
                                    ].map((feat, i) => (
                                        <li key={i} className="flex items-center gap-3 text-gray-700">
                                            <svg className="w-5 h-5 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                            {feat}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Sales Mode Card */}
                        <div className="flex flex-col h-full bg-gradient-to-b from-purple-50/50 to-white rounded-3xl border border-purple-100 p-8 md:p-10 overflow-hidden relative">
                            <div className="relative z-10">
                                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-100 text-purple-700 text-xs font-bold uppercase tracking-wider mb-6">
                                    Sales Mode
                                </div>
                                <h3 className="text-3xl font-bold text-gray-900 mb-4">Understand the buyer.</h3>
                                <p className="text-gray-600 mb-8 leading-relaxed">
                                    Move beyond call recording. Detect pricing objections, track sentiment shifts in real-time, and get AI-recommended follow-up actions to close the deal.
                                </p>
                                <ul className="space-y-3 mb-8">
                                    {[
                                        "Objection Detection & Classification",
                                        "Real-time Sentiment Trajectory",
                                        "Recommended Follow-up Actions",
                                        "Outcome Probability Signals"
                                    ].map((feat, i) => (
                                        <li key={i} className="flex items-center gap-3 text-gray-700">
                                            <svg className="w-5 h-5 text-purple-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                            {feat}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA / Footer */}
            <footer className="bg-gray-900 text-white py-20">
                <div className="max-w-4xl mx-auto px-6 text-center">
                    <h2 className="text-3xl font-bold mb-6">Ready to understand what matters?</h2>
                    <p className="text-gray-400 mb-10 text-lg">
                        Processing happens securely on your local engine. No data leaves your control without your permission.
                    </p>
                    <Link
                        to="/upload"
                        className="inline-flex items-center justify-center px-8 py-4 bg-white text-gray-900 font-bold rounded-xl hover:bg-gray-100 transition-colors"
                    >
                        Start Your First Analysis
                    </Link>

                    <div className="mt-16 pt-8 border-t border-gray-800 flex flex-col md:flex-row justify-between items-center text-gray-500 text-sm">
                        <p>© 2026 TalkSense AI. All rights reserved.</p>
                        <div className="flex gap-6 mt-4 md:mt-0">
                            <a href="#" className="hover:text-white transition-colors">Privacy</a>
                            <a href="#" className="hover:text-white transition-colors">Terms</a>
                            <a href="#" className="hover:text-white transition-colors">Contact</a>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    )
}
