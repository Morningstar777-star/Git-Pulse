import React, { useEffect, useRef } from 'react';
import { 
  Search, 
  Flame, 
  Trophy, 
  RefreshCw, 
  Bookmark, 
  Clock, 
  Hash,
  User as UserIcon,
  LogOut
} from 'lucide-react';
import { SortMode, TimeWindow, PopularitySortBy, SystemStatus, User } from '../types';
import { ThemeToggle } from './ThemeToggle';

interface HeaderProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  mode: SortMode;
  onModeChange: (m: SortMode) => void;
  timeWindow: TimeWindow;
  onTimeWindowChange: (w: TimeWindow) => void;
  popularitySortBy: PopularitySortBy;
  onPopularitySortChange: (s: PopularitySortBy) => void;
  watchlistCount: number;
  isWatchlistActive: boolean;
  onToggleWatchlistView: () => void;
  onOpenTopicsModal: () => void;
  totalTopicsCount: number;
  systemStatus: SystemStatus | null;
  onTriggerRefresh: () => void;
  user?: User | null;
  onOpenAuthModal?: () => void;
  onSignOut?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  searchQuery,
  onSearchChange,
  mode,
  onModeChange,
  timeWindow,
  onTimeWindowChange,
  popularitySortBy,
  onPopularitySortChange,
  watchlistCount,
  isWatchlistActive,
  onToggleWatchlistView,
  onOpenTopicsModal,
  totalTopicsCount,
  systemStatus,
  onTriggerRefresh,
  user,
  onOpenAuthModal,
  onSignOut
}) => {
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut: Press '/' to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== searchInputRef.current) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const getFirstName = (fullName?: string | null): string => {
    if (!fullName) return 'User';
    const first = fullName.trim().split(/\s+/)[0];
    if (!first) return 'User';
    return first.charAt(0).toUpperCase() + first.slice(1);
  };

  const formatLastSync = (iso: string | null | undefined) => {
    if (!iso) return 'Just now';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'Recently';
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full bg-white/90 dark:bg-[#0d1117]/90 backdrop-blur-md border-b border-slate-200 dark:border-[#30363d] px-3 lg:px-6 py-2.5 transition-colors">
      <div className="max-w-[1720px] mx-auto flex items-center justify-between gap-2 lg:gap-3 flex-nowrap">
        
        {/* Brand */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div 
            className="flex items-center gap-2 cursor-pointer group select-none" 
            onClick={() => window.location.reload()}
            title="Reload GitPulse Dashboard"
          >
            {/* Iconic Theme-Adaptive GitPulse Emblem */}
            <div className="relative flex items-center justify-center w-8 h-8 lg:w-9 lg:h-9 rounded-xl bg-slate-100 hover:bg-slate-200/80 dark:bg-[#161b22] dark:hover:bg-[#1f242c] border border-slate-200/90 dark:border-[#30363d] shadow-sm group-hover:border-blue-500/50 dark:group-hover:border-cyan-500/50 transition-all">
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
                {/* Git branch node circles */}
                <circle cx="4.5" cy="12" r="2.2" className="fill-blue-100 dark:fill-cyan-950/60 stroke-blue-600 dark:stroke-cyan-400" strokeWidth="1.8" />
                <circle cx="19.5" cy="6" r="2.2" className="fill-blue-100 dark:fill-cyan-950/60 stroke-blue-600 dark:stroke-cyan-400" strokeWidth="1.8" />
                <circle cx="19.5" cy="18" r="2.2" className="fill-blue-100 dark:fill-cyan-950/60 stroke-blue-600 dark:stroke-cyan-400" strokeWidth="1.8" />
                {/* EKG pulse waveform */}
                <path 
                  d="M6.8 12h2.2l1.8-6 2.8 12 2.2-8.5 1.5 2.5h1.7" 
                  className="stroke-blue-600 dark:stroke-cyan-400" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                />
                {/* Kinetic branch connection */}
                <path 
                  d="M15 9.5c1.2-1.3 2.3-2.5 2.3-2.5" 
                  className="stroke-indigo-500/60 dark:stroke-emerald-400/60" 
                  strokeWidth="1.6" 
                  strokeLinecap="round" 
                />
              </svg>
            </div>

            {/* Editorial Typographic Contrast */}
            <div className="flex flex-col leading-none">
              <h1 className="text-lg lg:text-xl font-extrabold tracking-[-0.03em] text-slate-900 dark:text-white flex items-center">
                Git<span className="font-serif italic font-normal text-[24px] lg:text-[26px] text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 dark:from-cyan-400 dark:via-sky-300 dark:to-emerald-400 ml-0.5">Pulse</span>
              </h1>
            </div>
          </div>

          {/* Topics Directory Pill (Clean, dot-free) */}
          <button
            onClick={onOpenTopicsModal}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200/80 dark:bg-[#161b22] dark:hover:bg-[#21262d] border border-slate-200 dark:border-[#30363d] text-xs font-mono text-slate-700 dark:text-slate-300 transition-all shadow-sm group shrink-0"
            title="Open 900+ Topics Directory"
          >
            <Hash className="w-3.5 h-3.5 text-blue-500 group-hover:rotate-12 transition-transform" />
            <span className="font-semibold hidden sm:inline">Topics</span>
            <span className="text-[11px] px-1.5 py-0.2 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-cyan-400 font-bold border border-blue-200/50 dark:border-blue-800/50">
              ({totalTopicsCount})
            </span>
          </button>
        </div>

        {/* Global Live Intelligence Search Bar - expands dynamically to available width */}
        <div className="relative flex-1 min-w-[140px] max-w-xs md:max-w-sm lg:max-w-md mx-1 lg:mx-2">
          <div className="relative flex items-center">
            <Search className="absolute left-3 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search repositories, topics... ('/')"
              className="w-full pl-9 pr-10 py-1.5 rounded-xl bg-slate-100 dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 dark:focus:border-blue-500 transition-all"
            />
            {searchQuery ? (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-3 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                esc
              </button>
            ) : (
              <kbd className="absolute right-3 px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-200 dark:bg-[#21262d] text-slate-500 dark:text-slate-400 border border-slate-300 dark:border-[#30363d] pointer-events-none hidden sm:inline-block">
                /
              </kbd>
            )}
          </div>
        </div>

        {/* Controls: Mode, Sub-Timeframe, Shortlist, Theme, Refresh - Strict Single-Row Non-Wrapping */}
        <div className="flex items-center gap-1.5 lg:gap-2 flex-nowrap shrink-0 justify-end">
          
          {/* Main Mode Selector: Momentum vs Popularity */}
          <div className="shrink-0 flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-xs font-mono">
            <button
              onClick={() => onModeChange('momentum')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium transition-all ${
                mode === 'momentum'
                  ? 'bg-white dark:bg-[#30363d] text-blue-600 dark:text-blue-400 shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Flame className="w-3.5 h-3.5 text-amber-500" />
              <span className="hidden sm:inline">Momentum</span>
            </button>

            <button
              onClick={() => onModeChange('popularity')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium transition-all ${
                mode === 'popularity'
                  ? 'bg-white dark:bg-[#30363d] text-amber-600 dark:text-amber-400 shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Trophy className="w-3.5 h-3.5 text-amber-500" />
              <span className="hidden sm:inline">Popularity</span>
            </button>
          </div>

          {/* Sub-Filters based on active Mode */}
          {mode === 'momentum' ? (
            <div className="shrink-0 flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-xs font-mono">
              {(['24h', '7d', '30d'] as TimeWindow[]).map((tw) => (
                <button
                  key={tw}
                  onClick={() => onTimeWindowChange(tw)}
                  className={`px-2 py-0.5 rounded transition-all ${
                    timeWindow === tw
                      ? 'bg-white dark:bg-[#30363d] text-blue-600 dark:text-blue-400 font-bold shadow-sm'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  {tw}
                </button>
              ))}
            </div>
          ) : (
            <div className="shrink-0 flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-xs font-mono">
              <button
                onClick={() => onPopularitySortChange('stars')}
                className={`px-2 py-0.5 rounded transition-all ${
                  popularitySortBy === 'stars'
                    ? 'bg-white dark:bg-[#30363d] text-amber-600 dark:text-amber-400 font-bold shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                Stars
              </button>
              <button
                onClick={() => onPopularitySortChange('forks')}
                className={`px-2 py-0.5 rounded transition-all ${
                  popularitySortBy === 'forks'
                    ? 'bg-white dark:bg-[#30363d] text-amber-600 dark:text-amber-400 font-bold shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                Forks
              </button>
            </div>
          )}

          {/* Shortlist Toggle */}
          <button
            onClick={onToggleWatchlistView}
            className={`shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              isWatchlistActive
                ? 'bg-amber-500 text-white border-amber-600 shadow-sm font-semibold'
                : 'bg-slate-100 dark:bg-[#21262d] border-slate-200 dark:border-transparent text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-[#30363d]'
            }`}
          >
            <Bookmark className={`w-3.5 h-3.5 ${isWatchlistActive ? 'fill-white' : 'text-slate-400'}`} />
            <span className="hidden sm:inline">Shortlist</span>
            {watchlistCount > 0 && (
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                isWatchlistActive ? 'bg-amber-700 text-white' : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
              }`}>
                {watchlistCount}
              </span>
            )}
          </button>

          {/* Optional User Auth Badge */}
          {user ? (
            <div 
              className="shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-[#161b22] border border-blue-200/80 dark:border-[#30363d] text-xs font-mono text-blue-700 dark:text-cyan-300"
              title={`Signed in as ${user.email}`}
            >
              <span className="font-semibold">{getFirstName(user.name)}</span>
              {onSignOut && (
                <button
                  onClick={onSignOut}
                  className="p-0.5 text-slate-400 hover:text-rose-500 transition-colors"
                  title="Sign out"
                >
                  <LogOut className="w-3 h-3" />
                </button>
              )}
            </div>
          ) : (
            onOpenAuthModal && (
              <button
                onClick={onOpenAuthModal}
                className="shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                title="Sign in (optional) to save watchlist"
              >
                <UserIcon className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
            )
          )}

          {/* Jhey Tompkins Night && Day Theme Toggle Switch (☀️ / 🌙) */}
          <div className="shrink-0 flex items-center">
            <ThemeToggle />
          </div>

          {/* Live Sync Trigger */}
          <button
            onClick={onTriggerRefresh}
            disabled={systemStatus?.is_refreshing}
            className={`shrink-0 p-1.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-slate-600 dark:text-slate-400 hover:text-blue-500 transition-all ${
              systemStatus?.is_refreshing ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            title={`Last synced: ${formatLastSync(systemStatus?.last_refresh_at)}. Click to sync now.`}
          >
            <RefreshCw className={`w-4 h-4 ${systemStatus?.is_refreshing ? 'animate-spin text-blue-500' : ''}`} />
          </button>

        </div>

      </div>
    </header>
  );
};
