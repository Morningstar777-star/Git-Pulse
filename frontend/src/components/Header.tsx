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
  user: User | null;
  onOpenAuthModal: () => void;
  onSignOut: () => void;
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
      <div className="max-w-[1720px] mx-auto flex flex-row items-center justify-between gap-2.5 lg:gap-4 flex-nowrap overflow-x-auto scrollbar-none">
        
        {/* Brand */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div 
            className="flex items-center gap-2 cursor-pointer group select-none" 
            onClick={() => window.location.reload()}
            title="Reload GitPulse Dashboard"
          >
            {/* Iconic Theme-Adaptive GitPulse Emblem */}
            <div className="relative flex items-center justify-center w-8 h-8 lg:w-9 lg:h-9 rounded-xl bg-slate-100 hover:bg-slate-200/80 dark:bg-[#161b22] dark:hover:bg-[#1f242c] border border-slate-200/90 dark:border-[#30363d] shadow-sm group-hover:border-blue-500/50 dark:group-hover:border-cyan-500/50 transition-all shrink-0">
              <svg className="w-4 h-4 lg:w-5 lg:h-5" viewBox="0 0 24 24" fill="none">
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
                Git<span className="font-serif italic font-normal text-[22px] lg:text-[26px] text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 dark:from-cyan-400 dark:via-sky-300 dark:to-emerald-400 ml-0.5">Pulse</span>
              </h1>
            </div>
          </div>

          {/* Topics Directory Pill (Clean, dot-free) */}
          <button
            onClick={onOpenTopicsModal}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-slate-100/90 dark:bg-[#161b22] hover:bg-slate-200/90 dark:hover:bg-[#1f242c] text-xs font-mono text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-[#30363d] shadow-sm transition-all group shrink-0"
            title="Browse all 900+ topics"
          >
            <Hash className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400 group-hover:scale-110 transition-transform" />
            <span className="font-medium hidden sm:inline">Topics</span>
            {totalTopicsCount > 0 && (
              <span className="text-[11px] font-semibold px-1.5 py-0.2 rounded-full bg-blue-100 dark:bg-cyan-950/60 text-blue-700 dark:text-cyan-300 border border-blue-200 dark:border-cyan-800/40">
                ({totalTopicsCount})
              </span>
            )}
          </button>
        </div>

        {/* Global Search Bar with Quick Clear */}
        <div className="relative flex-1 min-w-[150px] max-w-xs md:max-w-sm lg:max-w-md mx-1 lg:mx-2">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search repositories, topics, languages... ('/')"
            className="w-full pl-9 pr-14 py-1.5 text-xs lg:text-sm bg-slate-50 dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] rounded-lg text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-sans"
          />
          {searchQuery ? (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded text-xs"
              title="Clear search"
            >
              ✕
            </button>
          ) : (
            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-100 dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 pointer-events-none">
              /
            </kbd>
          )}
        </div>

        {/* Controls: Mode Switcher, Shortlist, Auth, Theme Toggle & Sync (Always in ONE single horizontal row) */}
        <div className="flex items-center flex-nowrap gap-2 shrink-0 justify-end">
          
          {/* Sorting Mode Toggle */}
          <div className="flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-xs shrink-0">
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
            <div className="flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-xs font-mono shrink-0">
              {(['24h', '7d', '30d'] as TimeWindow[]).map((tw) => (
                <button
                  key={tw}
                  onClick={() => onTimeWindowChange(tw)}
                  className={`px-1.5 lg:px-2 py-0.5 rounded transition-all ${
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
            <div className="flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-xs font-mono shrink-0">
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
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all shrink-0 ${
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

          {/* Optional User Auth / Profile Badge */}
          {user ? (
            <div className="flex items-center gap-1 pl-1 border-l border-slate-200 dark:border-[#30363d] shrink-0">
              <div 
                className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200/80 dark:border-blue-900/60 text-xs font-mono text-blue-700 dark:text-cyan-300 shrink-0"
                title={`Signed in as ${user.email}`}
              >
                <div className="w-4 h-4 rounded-full bg-blue-600 text-white font-bold text-[9px] flex items-center justify-center shrink-0">
                  {(getFirstName(user.name)[0] || 'U').toUpperCase()}
                </div>
                <span className="font-semibold whitespace-nowrap">{getFirstName(user.name)}</span>
              </div>
              <button
                onClick={onSignOut}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-slate-100 dark:hover:bg-[#21262d] transition-colors shrink-0"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuthModal}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono font-medium bg-slate-100 hover:bg-slate-200/80 dark:bg-[#161b22] dark:hover:bg-[#21262d] border border-slate-200 dark:border-[#30363d] text-slate-700 dark:text-slate-300 transition-all shadow-sm shrink-0"
              title="Sign in (optional) to save personal bookmarks"
            >
              <UserIcon className="w-3.5 h-3.5 text-blue-500" />
              <span>Sign In</span>
              <span className="text-[10px] text-slate-400 hidden sm:inline">(Optional)</span>
            </button>
          )}

          {/* Theme Toggle & Live Sync Trigger (Always together on same horizontal line) */}
          <div className="flex items-center gap-1.5 shrink-0 pl-1 border-l border-slate-200 dark:border-[#30363d]">
            <ThemeToggle className="shrink-0" />
            <button
              onClick={onTriggerRefresh}
              disabled={systemStatus?.is_refreshing}
              className={`p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200/80 dark:bg-[#161b22] dark:hover:bg-[#21262d] border border-slate-200 dark:border-[#30363d] text-slate-600 dark:text-slate-400 hover:text-blue-500 dark:hover:text-cyan-400 transition-all shrink-0 ${
                systemStatus?.is_refreshing ? 'opacity-50 cursor-not-allowed' : ''
              }`}
              title={`Last synced: ${formatLastSync(systemStatus?.last_refresh_at)}. Click to sync now.`}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${systemStatus?.is_refreshing ? 'animate-spin text-blue-500' : ''}`} />
            </button>
          </div>

        </div>

      </div>
    </header>
  );
};
