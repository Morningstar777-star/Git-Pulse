import React, { useEffect, useRef } from 'react';
import { 
  Search, 
  Flame, 
  Trophy, 
  RefreshCw, 
  Bookmark, 
  Clock, 
  Hash
} from 'lucide-react';
import { SortMode, TimeWindow, PopularitySortBy, SystemStatus } from '../types';
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
  onTriggerRefresh
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
    <header className="sticky top-0 z-40 w-full bg-white/90 dark:bg-[#0d1117]/90 backdrop-blur-md border-b border-slate-200 dark:border-[#30363d] px-4 lg:px-6 py-3 transition-colors">
      <div className="max-w-[1720px] mx-auto flex flex-col md:flex-row items-center justify-between gap-3.5">
        
        {/* Brand */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => window.location.reload()}>
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-600 text-white font-bold font-mono text-sm shadow-sm">
              GP
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-1.5">
                GitPulse
              </h1>
            </div>
          </div>

          {/* Topics Directory Pill */}
          <button
            onClick={onOpenTopicsModal}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-[#21262d] hover:bg-slate-200 dark:hover:bg-[#30363d] text-xs font-mono text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-transparent transition-colors"
            title="Browse all 900+ topics"
          >
            <Hash className="w-3.5 h-3.5 text-blue-500" />
            <span>Topics</span>
            {totalTopicsCount > 0 && (
              <span className="text-[10px] text-slate-500 dark:text-slate-400 font-semibold">
                ({totalTopicsCount})
              </span>
            )}
          </button>
        </div>

        {/* Global Search Bar */}
        <div className="relative w-full md:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search repositories, topics, languages... ('/')"
            className="w-full pl-9 pr-10 py-1.5 text-sm bg-slate-50 dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] rounded-lg text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-sans"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-100 dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 pointer-events-none">
            /
          </kbd>
        </div>

        {/* Controls: Mode Switcher, Shortlist & Theme Toggle */}
        <div className="flex items-center flex-wrap gap-2.5 w-full md:w-auto justify-end">
          
          {/* Sorting Mode Toggle */}
          <div className="flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-xs">
            <button
              onClick={() => onModeChange('momentum')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all ${
                mode === 'momentum'
                  ? 'bg-white dark:bg-[#30363d] text-blue-600 dark:text-blue-400 shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Flame className="w-3.5 h-3.5 text-amber-500" />
              <span>Momentum</span>
            </button>

            <button
              onClick={() => onModeChange('popularity')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all ${
                mode === 'popularity'
                  ? 'bg-white dark:bg-[#30363d] text-amber-600 dark:text-amber-400 shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Trophy className="w-3.5 h-3.5 text-amber-500" />
              <span>Popularity</span>
            </button>
          </div>

          {/* Sub-Filters based on active Mode */}
          {mode === 'momentum' ? (
            <div className="flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-xs font-mono">
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
            <div className="flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-xs font-mono">
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
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              isWatchlistActive
                ? 'bg-amber-500 text-white border-amber-600 shadow-sm font-semibold'
                : 'bg-slate-100 dark:bg-[#21262d] border-slate-200 dark:border-transparent text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-[#30363d]'
            }`}
          >
            <Bookmark className={`w-3.5 h-3.5 ${isWatchlistActive ? 'fill-white' : 'text-slate-400'}`} />
            <span>Shortlist</span>
            {watchlistCount > 0 && (
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                isWatchlistActive ? 'bg-amber-700 text-white' : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
              }`}>
                {watchlistCount}
              </span>
            )}
          </button>

          {/* Jhey Tompkins Night && Day Theme Toggle Switch (☀️ / 🌙) */}
          <ThemeToggle />

          {/* Live Sync Trigger */}
          <button
            onClick={onTriggerRefresh}
            disabled={systemStatus?.is_refreshing}
            className={`p-1.5 rounded-lg bg-slate-100 dark:bg-[#21262d] border border-slate-200 dark:border-transparent text-slate-600 dark:text-slate-400 hover:text-blue-500 transition-all ${
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
