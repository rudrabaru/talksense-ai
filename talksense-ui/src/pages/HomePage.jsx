import { useNavigate } from "react-router-dom"
import logoImage from "../assets/logo/logo.png"

export default function HomePage() {
    const navigate = useNavigate()
    return (
        <div className="min-h-screen bg-white">
            {/* Navbar - Full Width with Contained Content */}
            <nav className="border-b border-gray-200 bg-white sticky top-0 z-50 backdrop-blur-sm bg-white/95">
                <div className="mx-auto px-6 lg:px-12 xl:px-16 h-16 flex items-center justify-between">
                    <button
                        onClick={() => navigate('/')}
                        className="flex items-center gap-3 hover:opacity-80 transition-opacity"
                    >
                        {/* Logo */}
                        <div className="relative w-9 h-9">
                            <img src={logoImage} alt="TalkSense AI Logo" className="w-full h-full object-contain" />
                        </div>
                        <span className="font-bold text-xl tracking-tight">
                            <span style={{ color: '#4F46E5' }}>TalkSense</span>
                            <span style={{ color: '#14B8A6' }}> AI</span>
                        </span>
                    </button>
                    <div className="hidden md:flex gap-8 text-sm font-medium text-gray-600">
                        <a href="#how-it-works" className="hover:text-indigo-600 transition-colors">How it Works</a>
                        <a href="#solutions" className="hover:text-indigo-600 transition-colors">Solutions</a>
                    </div>
                    <div>
                        <button
                            onClick={() => navigate('/upload')}
                            className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-semibold rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-smooth shadow-sm hover:shadow-md hover-lift active:scale-95"
                        >
                            Start Analysis
                        </button>
                    </div>
                </div>
            </nav>

            {/* Hero Section - Asymmetric Full Width */}
            <header className="relative overflow-hidden bg-gradient-to-br from-gray-50 via-white to-indigo-50/30">
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-indigo-50/40 to-transparent"></div>
                    <div className="absolute bottom-0 left-0 w-1/3 h-1/2 bg-gradient-to-tr from-teal-50/30 to-transparent"></div>
                </div>

                <div className="relative mx-auto px-6 lg:px-12 xl:px-16 py-20 lg:py-32">
                    <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
                        {/* Left Column - Content */}
                        <div className="max-w-2xl">
                            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 text-indigo-700 text-sm font-medium mb-6 border border-indigo-100">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                                </span>
                                Conversation Intelligence Platform
                            </div>

                            <h1 className="text-5xl lg:text-6xl xl:text-7xl font-bold text-gray-900 tracking-tight mb-6 leading-[1.1]">
                                Turn conversations into{" "}
                                <span className="text-indigo-600">clarity</span>.
                            </h1>

                            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
                                Extract decisions, track sentiment shifts, and identify risks from your most important discussions. Move from noise to understanding in seconds.
                            </p>

                            <div className="flex flex-col sm:flex-row gap-4">
                                <button
                                    onClick={() => navigate('/upload')}
                                    className="inline-flex items-center justify-center px-8 py-4 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-smooth shadow-lg hover:shadow-xl hover-lift active:scale-95"
                                >
                                    Analyze Conversation
                                    <svg className="w-5 h-5 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                    </svg>
                                </button>
                                <button
                                    onClick={() => navigate('/upload')}
                                    className="inline-flex items-center justify-center px-8 py-4 bg-white text-gray-700 font-semibold rounded-xl border-2 border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-smooth hover-lift active:scale-95"
                                >
                                    Try Demo
                                </button>
                            </div>
                        </div>

                        {/* Right Column - Visual Element */}
                        <div className="hidden lg:block relative">
                            <div className="relative bg-white rounded-2xl shadow-2xl border border-gray-200 p-6 transform rotate-2 hover:rotate-0 transition-transform duration-500">
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3 pb-3 border-b border-gray-100">
                                        <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
                                            <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                            </svg>
                                        </div>
                                        <div>
                                            <div className="text-sm font-semibold text-gray-900">Sales Call Analysis</div>
                                            <div className="text-xs text-gray-500">32:45 duration</div>
                                        </div>
                                    </div>
                                    <div className="space-y-3">
                                        <div className="h-3 bg-gray-100 rounded-full w-full"></div>
                                        <div className="h-3 bg-teal-100 rounded-full w-4/5"></div>
                                        <div className="h-3 bg-indigo-100 rounded-full w-3/5"></div>
                                        <div className="flex items-center gap-2 pt-2">
                                            <span className="px-2 py-1 bg-teal-50 text-teal-700 text-xs font-medium rounded">High Quality</span>
                                            <span className="px-2 py-1 bg-indigo-50 text-indigo-700 text-xs font-medium rounded">3 Decisions</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* How it Works - Full Width Grid */}
            <section id="how-it-works" className="py-20 lg:py-28 bg-white">
                <div className="mx-auto px-6 lg:px-12 xl:px-16">
                    <div className="text-center mb-16 max-w-3xl mx-auto">
                        <h2 className="text-4xl font-bold text-gray-900 mb-4">How it works</h2>
                        <p className="text-lg text-gray-600">A streamlined workflow designed for professionals who value their time.</p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8 lg:gap-12">
                        {[
                            {
                                step: "01",
                                title: "Upload Audio",
                                desc: "Securely upload your meeting recording or sales call. Privacy-first processing with enterprise-grade encryption.",
                                icon: (
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                ),
                                color: "indigo"
                            },
                            {
                                step: "02",
                                title: "AI Analysis",
                                desc: "Advanced models detect sentiment, extract decisions, and identify friction points with context-aware understanding.",
                                icon: (
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                    </svg>
                                ),
                                color: "teal"
                            },
                            {
                                step: "03",
                                title: "Act on Insights",
                                desc: "Receive structured summaries, action items with owners, and strategic recommendations instantly.",
                                icon: (
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                ),
                                color: "indigo"
                            }
                        ].map((item, i) => (
                            <div key={i} className="relative bg-gray-50 p-8 rounded-2xl border border-gray-200 hover:border-indigo-200 hover:shadow-lg transition-smooth group hover-lift">
                                <div className="absolute top-4 right-4 text-6xl font-black text-gray-100 select-none group-hover:text-indigo-50 transition-colors">
                                    {item.step}
                                </div>
                                <div className={`w-14 h-14 bg-${item.color}-100 rounded-xl flex items-center justify-center mb-6 text-${item.color}-600 group-hover:scale-110 transition-transform`}>
                                    {item.icon}
                                </div>
                                <h3 className="text-xl font-bold text-gray-900 mb-3">{item.title}</h3>
                                <p className="text-gray-600 leading-relaxed">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Solutions - Side by Side Full Width */}
            <section id="solutions" className="py-20 lg:py-28 bg-gradient-to-b from-gray-50 to-white">
                <div className="mx-auto px-6 lg:px-12 xl:px-16">
                    <div className="text-center mb-16 max-w-3xl mx-auto">
                        <h2 className="text-4xl font-bold text-gray-900 mb-4">Built for your workflow</h2>
                        <p className="text-lg text-gray-600">Specialized intelligence for meetings and sales conversations.</p>
                    </div>

                    <div className="grid lg:grid-cols-2 gap-8">
                        {/* Meeting Mode */}
                        <div className="bg-white rounded-2xl border-2 border-indigo-100 p-10 hover:border-indigo-200 hover:shadow-xl transition-smooth hover-lift">
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold uppercase tracking-wider mb-6">
                                Meeting Mode
                            </div>
                            <h3 className="text-3xl font-bold text-gray-900 mb-4">Align your team</h3>
                            <p className="text-gray-600 mb-8 leading-relaxed text-lg">
                                Stop wondering what was decided. Capture key decisions, map action items to owners, and flag unresolved tension.
                            </p>
                            <ul className="space-y-4">
                                {[
                                    "Automated Executive Summaries",
                                    "Action Item & Deadline Tracking",
                                    "Decision Documentation",
                                    "Tension & Blocker Detection"
                                ].map((feat, i) => (
                                    <li key={i} className="flex items-center gap-3 text-gray-700">
                                        <div className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                                            <svg className="w-3 h-3 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                            </svg>
                                        </div>
                                        <span className="font-medium">{feat}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Sales Mode */}
                        <div className="bg-white rounded-2xl border-2 border-teal-100 p-10 hover:border-teal-200 hover:shadow-xl transition-smooth hover-lift">
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-teal-50 text-teal-700 text-xs font-bold uppercase tracking-wider mb-6">
                                Sales Mode
                            </div>
                            <h3 className="text-3xl font-bold text-gray-900 mb-4">Understand buyers</h3>
                            <p className="text-gray-600 mb-8 leading-relaxed text-lg">
                                Move beyond call recording. Detect pricing objections, track sentiment shifts, and get AI-recommended follow-ups.
                            </p>
                            <ul className="space-y-4">
                                {[
                                    "Objection Detection & Classification",
                                    "Real-time Sentiment Analysis",
                                    "Strategic Follow-up Actions",
                                    "Deal Probability Signals"
                                ].map((feat, i) => (
                                    <li key={i} className="flex items-center gap-3 text-gray-700">
                                        <div className="w-5 h-5 rounded-full bg-teal-100 flex items-center justify-center flex-shrink-0">
                                            <svg className="w-3 h-3 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                            </svg>
                                        </div>
                                        <span className="font-medium">{feat}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA / Footer */}
            <footer className="bg-gray-900 text-white py-20">
                <div className="mx-auto px-6 lg:px-12 xl:px-16">
                    <div className="max-w-4xl mx-auto text-center mb-16">
                        <h2 className="text-4xl font-bold mb-6">Ready to understand what matters?</h2>
                        <p className="text-gray-400 mb-10 text-lg">
                            Enterprise-grade security. Local processing options. No data leaves your control without permission.
                        </p>
                        <button
                            onClick={() => navigate('/upload')}
                            className="inline-flex items-center justify-center px-10 py-4 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-smooth shadow-lg hover:shadow-xl hover-lift active:scale-95"
                        >
                            Start Your First Analysis
                        </button>
                    </div>

                    <div className="pt-12 border-t border-gray-800 flex flex-col md:flex-row justify-between items-center text-gray-400 text-sm">
                        <p>© 2026 TalkSense AI. All rights reserved.</p>
                        <div className="flex gap-8 mt-4 md:mt-0">
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