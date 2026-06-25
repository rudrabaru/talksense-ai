import React from 'react';

/**
 * Premium Client Briefing Card Component
 * Shown before starting a session to provide relationship context and memory profile.
 */
export default function ClientBriefingCard({ client, loading }) {
    if (loading) {
        return (
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm animate-pulse">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <div className="h-6 w-48 bg-gray-200 rounded mb-2"></div>
                        <div className="h-4 w-32 bg-gray-100 rounded"></div>
                    </div>
                    <div className="h-8 w-24 bg-gray-200 rounded-full"></div>
                </div>
                
                <div className="grid grid-cols-3 gap-4 mb-6">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="bg-gray-50 p-3 rounded-xl">
                            <div className="h-4 w-16 bg-gray-200 rounded mb-2 mx-auto"></div>
                            <div className="h-6 w-10 bg-gray-300 rounded mx-auto"></div>
                        </div>
                    ))}
                </div>

                <div className="mb-6">
                    <div className="h-4 w-28 bg-gray-200 rounded mb-3"></div>
                    <div className="h-4 w-full bg-gray-150 rounded mb-2"></div>
                    <div className="h-4 w-5/6 bg-gray-150 rounded"></div>
                </div>

                <div>
                    <div className="h-4 w-36 bg-gray-200 rounded mb-3"></div>
                    <div className="flex gap-2">
                        <div className="h-6 w-16 bg-gray-200 rounded-full"></div>
                        <div className="h-6 w-20 bg-gray-200 rounded-full"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (!client) return null;

    const {
        name,
        industry,
        meetings_count = 0,
        sentiment_trend,
        common_objections = [],
        last_meeting_date,
        summary
    } = client;

    // Trend badge styling
    let trendColor = 'bg-slate-50 text-slate-700 border-slate-200';
    let trendLabel = 'No History';
    
    if (sentiment_trend === 'improving') {
        trendColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
        trendLabel = 'Improving';
    } else if (sentiment_trend === 'declining') {
        trendColor = 'bg-rose-50 text-rose-700 border-rose-200';
        trendLabel = 'Declining';
    } else if (sentiment_trend === 'stable') {
        trendColor = 'bg-blue-50 text-blue-700 border-blue-200';
        trendLabel = 'Stable';
    }

    // Format last meeting date
    const formattedDate = last_meeting_date
        ? new Date(last_meeting_date).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
              year: 'numeric'
          })
        : 'Never';

    return (
        <div className="bg-white rounded-2xl border border-gray-150 p-6 shadow-sm hover:shadow-md transition-smooth animate-fade-in">
            {/* Header */}
            <div className="flex justify-between items-start mb-5">
                <div>
                    <h3 className="text-xl font-bold text-gray-900 leading-tight">{name}</h3>
                    <p className="text-sm font-medium text-gray-500 mt-0.5">{industry || 'General Industry'}</p>
                </div>
                {meetings_count > 0 && (
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${trendColor} flex items-center gap-1.5`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${
                            sentiment_trend === 'improving' ? 'bg-emerald-500' :
                            sentiment_trend === 'declining' ? 'bg-rose-500' :
                            sentiment_trend === 'stable' ? 'bg-blue-500' : 'bg-slate-400'
                        }`}></span>
                        Trend: {trendLabel}
                    </span>
                )}
            </div>

            {/* Quick Metrics */}
            <div className="grid grid-cols-3 gap-4 mb-5">
                <div className="bg-slate-50 p-3 rounded-xl text-center border border-slate-100">
                    <span className="block text-xs font-medium text-gray-500 uppercase tracking-wider">Meetings</span>
                    <span className="text-lg font-bold text-gray-900 mt-1 block">{meetings_count}</span>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl text-center border border-slate-100 col-span-2">
                    <span className="block text-xs font-medium text-gray-500 uppercase tracking-wider">Last Interaction</span>
                    <span className="text-base font-bold text-gray-900 mt-1 block truncate">{formattedDate}</span>
                </div>
            </div>

            {/* Relationship Briefing */}
            <div className="mb-5 bg-indigo-50/40 border border-indigo-100/50 rounded-xl p-4">
                <h4 className="text-xs font-semibold text-indigo-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    Relationship Briefing
                </h4>
                <p className="text-sm text-gray-700 leading-relaxed font-normal">
                    {summary || (meetings_count === 0 
                        ? "New client. No relationship summary available yet. Real-time feedback will build this profile during your first meeting."
                        : "No summary briefing available for this client snapshot.")}
                </p>
            </div>

            {/* Objections */}
            {meetings_count > 0 && (
                <div>
                    <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        Common Objections
                    </h4>
                    {common_objections.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                            {common_objections.map((obj, i) => (
                                <span key={i} className="px-2.5 py-0.5 bg-rose-50 text-rose-700 border border-rose-100 rounded-lg text-xs font-medium">
                                    {obj}
                                </span>
                            ))}
                        </div>
                    ) : (
                        <p className="text-xs text-gray-400 italic">No objections recorded in previous meetings.</p>
                    )}
                </div>
            )}
        </div>
    );
}
