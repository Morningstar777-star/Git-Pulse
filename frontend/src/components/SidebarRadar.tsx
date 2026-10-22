import React, { useState } from 'react';
import { 
  Flame, 
  ExternalLink, 
  Bookmark, 
  ArrowUpRight,
  TrendingUp,
  ChevronDown,
  ArrowUpDown,
  ArrowUp,
  ArrowDown
} from 'lucide-react';
import { Repository, TimeWindow } from '../types';
import { RepoAvatar } from './RepoAvatar';

interface SidebarRadarProps {
  repositories: Repository[];
  timeWindow: TimeWindow;
  onSelectRepository: (repo: Repository) => void;
  onToggleWatchlist: (repoId: number) => void;
  onSelectTopic: (topic: string) => void;
  onLoadMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
}

function getAvatarColor(name: string): string {
  const colors = [
    'bg-blue-600 text-white',
    'bg-purple-600 text-white',
    'bg-emerald-600 text-white',
    'bg-amber-600 text-white',
    'bg-rose-600 text-white',
    'bg-indigo-600 text-white',
    'bg-cyan-600 text-white',
    'bg-teal-600 text-white'
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

function formatStars(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
  return num.toString();
}

type RadarSortCol = 'stars' | '1d' | '7d' | '30d' | 'per_day';

export const SidebarRadar: React.FC<SidebarRadarProps> = ({
  repositories,
  timeWindow,
  onSelectRepository,
  onToggleWatchlist,
  onSelectTopic,
  onLoadMore,
  hasMore,
  isLoading
}) => {
  const [sortCol, setSortCol] = useState<RadarSortCol>('per_day');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  const handleSortClick = (col: RadarSortCol) => {
    if (sortCol === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(col);
      setSortAsc(false); // default desc
    }
  };

  const sortedRepos = [...repositories].sort((a, b) => {
    let diff = 0;
    if (sortCol === 'stars') {
      diff = a.stars - b.stars;
    } else if (sortCol === '1d') {
      diff = (a.growth_1d_pct ?? 0) - (b.growth_1d_pct ?? 0);
    } else if (sortCol === '7d') {
      diff = (a.growth_7d_pct ?? 0) - (b.growth_7d_pct ?? 0);
    } else if (sortCol === '30d') {
      diff = (a.growth_30d_pct ?? 0) - (b.growth_30d_pct ?? 0);
    } else if (sortCol === 'per_day') {
      diff = a.stars_per_day - b.stars_per_day;
    }
    return sortAsc ? diff : -diff;
  });

  const renderSortIndicator = (col: RadarSortCol) => {
    if (sortCol !== col) return null;
    return sortAsc ? (
      <ArrowUp className="w-2.5 h-2.5 text-blue-500 inline ml-0.5" />
    ) : (
      <ArrowDown className="w-2.5 h-2.5 text-blue-500 inline ml-0.5" />
    );
  };

  return (
    <aside className="w-full xl:w-[480px] 2xl:w-[520px] shrink-0 border-l border-slate-200 dark:border-[#30363d] bg-white dark:bg-[#0d1117] flex flex-col h-full overflow-hidden">
      
      {/* Header section matching reference image */}
      <div className="p-4 border-b border-slate-200 dark:border-[#30363d] space-y-1">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
            <span>Highest momentum</span>
          </h2>
          <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-medium">
            Live Stream
          </span>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 font-sans">
          A selection of {repositories.length}+ repositories. Ranked by daily velocity.
        </p>

        {/* Column Headers with Interactive Sorting */}
        <div className="flex items-center justify-between text-[11px] font-mono font-semibold text-slate-400 dark:text-slate-500 pt-3 border-t border-slate-100 dark:border-[#21262d] mt-2 select-none">
          <span className="w-48 sm:w-56 truncate">REPOSITORY</span>
          <div className="flex items-center gap-3 text-right">
            <button 
              onClick={() => handleSortClick('stars')}
              className={`w-12 hover:text-slate-900 dark:hover:text-white transition-colors ${sortCol === 'stars' ? 'text-blue-500 font-bold' : ''}`}
            >
              STARS {renderSortIndicator('stars')}
            </button>
            <button 
              onClick={() => handleSortClick('1d')}
              className={`w-10 hover:text-slate-900 dark:hover:text-white transition-colors ${sortCol === '1d' ? 'text-blue-500 font-bold' : ''}`}
            >
              1D {renderSortIndicator('1d')}
            </button>
            <button 
              onClick={() => handleSortClick('7d')}
              className={`w-10 hover:text-slate-900 dark:hover:text-white transition-colors ${sortCol === '7d' ? 'text-blue-500 font-bold' : ''}`}
            >
              7D {renderSortIndicator('7d')}
            </button>
            <button 
              onClick={() => handleSortClick('30d')}
              className={`w-10 hidden sm:inline hover:text-slate-900 dark:hover:text-white transition-colors ${sortCol === '30d' ? 'text-blue-500 font-bold' : ''}`}
            >
              30D {renderSortIndicator('30d')}
            </button>
            <button 
              onClick={() => handleSortClick('per_day')}
              className={`w-14 text-right hover:text-slate-900 dark:hover:text-white transition-colors ${sortCol === 'per_day' ? 'text-blue-500 font-bold' : 'text-slate-700 dark:text-slate-200'}`}
            >
              PER DAY {renderSortIndicator('per_day') || '▼'}
            </button>
          </div>
        </div>
      </div>

      {/* Infinite scrolling list */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-[#21262d] p-1">
        {sortedRepos.map((repo, idx) => {
          const rank = idx + 1;
          const initial = (repo.name[0] || 'R').toUpperCase();
          const avatarClass = getAvatarColor(repo.name);

          return (
            <div
              key={repo.id}
              onClick={() => onSelectRepository(repo)}
              className="p-3 hover:bg-slate-50 dark:hover:bg-[#161b22] transition-colors cursor-pointer group flex flex-col gap-1.5"
            >
              {/* Top row: Rank, Monogram Avatar, Repo Full Name, Telemetry Columns */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs font-mono text-slate-400 dark:text-slate-500 w-4 shrink-0 text-right">
                    {rank}
                  </span>

                  {/* Owner / Org Logo (or Letter Monogram Fallback) */}
                  <RepoAvatar owner={repo.owner} name={repo.name} size="sm" />

                  {/* Full Name */}
                  <div className="min-w-0 truncate">
                    <span className="text-xs font-bold text-blue-600 dark:text-blue-400 group-hover:underline truncate block">
                      {repo.full_name}
                    </span>
                  </div>
                </div>

                {/* Metric Columns */}
                <div className="flex items-center gap-3 text-right text-xs font-mono shrink-0">
                  <span className="w-12 text-slate-700 dark:text-slate-300">
                    {formatStars(repo.stars)}
                  </span>

                  <span className="w-10 text-emerald-600 dark:text-emerald-400 font-medium">
                    +{repo.growth_1d_pct ?? 0.5}%
                  </span>

                  <span className="w-10 text-emerald-600 dark:text-emerald-400 font-medium">
                    +{repo.growth_7d_pct ?? 3.2}%
                  </span>

                  <span className="w-10 text-slate-400 dark:text-slate-500 hidden sm:inline">
                    {repo.growth_30d_pct ? `+${repo.growth_30d_pct}%` : '—'}
                  </span>

                  <span className="w-14 text-slate-900 dark:text-white font-bold">
                    {repo.stars_per_day.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Description */}
              {repo.description && (
                <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2 pl-12 font-sans leading-relaxed">
                  {repo.description}
                </p>
              )}

              {/* Topic Pills Row */}
              <div className="flex items-center justify-between pl-12 pt-0.5">
                <div className="flex items-center gap-1.5 flex-wrap">
                  {repo.topics.slice(0, 3).map((t) => (
                    <button
                      key={t}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectTopic(t);
                      }}
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-[#21262d] text-slate-600 dark:text-slate-400 hover:text-blue-500 hover:bg-slate-200 dark:hover:bg-[#30363d] transition-colors"
                    >
                      {t}
                    </button>
                  ))}
                  {repo.language && (
                    <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                      • {repo.language}
                    </span>
                  )}
                </div>

                {/* Bookmark Toggle */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleWatchlist(repo.id);
                  }}
                  className="p-1 text-slate-400 hover:text-amber-500 transition-colors"
                  title={repo.is_saved ? "Remove from Shortlist" : "Add to Shortlist"}
                >
                  <Bookmark className={`w-3.5 h-3.5 ${repo.is_saved ? 'fill-amber-500 text-amber-500' : ''}`} />
                </button>
              </div>

            </div>
          );
        })}

        {/* Infinite Scroll / Load More Trigger */}
        <div className="p-4 text-center">
          {hasMore ? (
            <button
              onClick={onLoadMore}
              disabled={isLoading}
              className="w-full py-2 px-4 rounded-lg bg-slate-100 dark:bg-[#21262d] hover:bg-slate-200 dark:hover:bg-[#30363d] text-xs font-mono text-slate-700 dark:text-slate-300 font-medium transition-colors flex items-center justify-center gap-1.5"
            >
              <ChevronDown className="w-3.5 h-3.5" />
              <span>{isLoading ? "Loading more..." : "Load More Momentum Repos"}</span>
            </button>
          ) : (
            <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
              End of momentum radar
            </span>
          )}
        </div>

      </div>

    </aside>
  );
};
