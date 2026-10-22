import React, { useState, useRef } from 'react';
import { 
  Star, 
  GitFork, 
  ExternalLink, 
  Bookmark, 
  Flame, 
  ArrowUpRight,
  Filter,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ArrowUpDown,
  ArrowUp,
  ArrowDown
} from 'lucide-react';
import { Repository, TopicCategory, SortMode } from '../types';
import { RepoAvatar } from './RepoAvatar';

interface TopicExplorerProps {
  repositories: Repository[];
  topics: TopicCategory[];
  activeCategoryId: string | null;
  activeTopic: string | null;
  onSelectCategory: (catId: string | null) => void;
  onSelectTopic: (topic: string | null) => void;
  onSelectRepository: (repo: Repository) => void;
  onToggleWatchlist: (repoId: number) => void;
  isShortlistView: boolean;
  onLoadMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
  sortMode: SortMode;
}

function getAvatarColor(name: string): string {
  const colors = [
    'bg-blue-600 text-white',
    'bg-purple-600 text-white',
    'bg-emerald-600 text-white',
    'bg-amber-600 text-white',
    'bg-rose-600 text-white',
    'bg-indigo-600 text-white',
    'bg-cyan-600 text-white'
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

type ShortlistSortKey = 'name' | 'stars' | '1d' | '7d' | '30d' | 'per_day' | 'momentum';

export const TopicExplorer: React.FC<TopicExplorerProps> = ({
  repositories,
  topics,
  activeCategoryId,
  activeTopic,
  onSelectCategory,
  onSelectTopic,
  onSelectRepository,
  onToggleWatchlist,
  isShortlistView,
  onLoadMore,
  hasMore,
  isLoading,
  sortMode
}) => {
  // Shortlist column sorting state
  const [shortlistSortKey, setShortlistSortKey] = useState<ShortlistSortKey>('per_day');
  const [shortlistSortAsc, setShortlistSortAsc] = useState<boolean>(false);

  const handleShortlistSort = (key: ShortlistSortKey) => {
    if (shortlistSortKey === key) {
      setShortlistSortAsc(!shortlistSortAsc);
    } else {
      setShortlistSortKey(key);
      setShortlistSortAsc(false); // default descending for metrics
    }
  };

  // Sort shortlist repositories
  const sortedShortlist = [...repositories].sort((a, b) => {
    let diff = 0;
    if (shortlistSortKey === 'name') {
      diff = a.name.localeCompare(b.name);
    } else if (shortlistSortKey === 'stars') {
      diff = a.stars - b.stars;
    } else if (shortlistSortKey === '1d') {
      diff = (a.growth_1d_pct ?? 0) - (b.growth_1d_pct ?? 0);
    } else if (shortlistSortKey === '7d') {
      diff = (a.growth_7d_pct ?? 0) - (b.growth_7d_pct ?? 0);
    } else if (shortlistSortKey === '30d') {
      diff = (a.growth_30d_pct ?? 0) - (b.growth_30d_pct ?? 0);
    } else if (shortlistSortKey === 'per_day') {
      diff = a.stars_per_day - b.stars_per_day;
    } else if (shortlistSortKey === 'momentum') {
      diff = a.momentum_score - b.momentum_score;
    }
    return shortlistSortAsc ? diff : -diff;
  });

  // -------------------------------------------------------------
  // TABULAR SHORTLIST VIEW
  // -------------------------------------------------------------
  if (isShortlistView) {
    if (repositories.length === 0) {
      return (
        <main className="flex-1 p-8 lg:p-14 flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] flex items-center justify-center text-slate-400 mb-4 shadow-sm">
            <Bookmark className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
            Shortlist is Empty (null)
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md font-sans leading-relaxed">
            You haven't bookmarked any repositories yet. Click the bookmark icon on any repository to add it to your shortlist table for side-by-side comparison.
          </p>
        </main>
      );
    }

    const renderSortArrow = (key: ShortlistSortKey) => {
      if (shortlistSortKey !== key) {
        return <ArrowUpDown className="w-3 h-3 text-slate-400 opacity-60 inline ml-1" />;
      }
      return shortlistSortAsc ? (
        <ArrowUp className="w-3 h-3 text-blue-500 inline ml-1" />
      ) : (
        <ArrowDown className="w-3 h-3 text-blue-500 inline ml-1" />
      );
    };

    return (
      <main className="flex-1 overflow-y-auto px-4 lg:px-8 py-6 space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-[#30363d]">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Bookmark className="w-5 h-5 text-amber-500 fill-amber-500" />
              Shortlisted Repositories
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
              {repositories.length} repositories saved • Click column headers to sort
            </p>
          </div>
        </div>

        {/* Tabular View */}
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-[#30363d] bg-white dark:bg-[#161b22] shadow-sm">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-[#30363d] bg-slate-50 dark:bg-[#0d1117] text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                <th className="py-3 px-3 w-10 text-center">#</th>
                <th 
                  onClick={() => handleShortlistSort('name')}
                  className="py-3 px-4 cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  REPOSITORY {renderSortArrow('name')}
                </th>
                <th 
                  onClick={() => handleShortlistSort('stars')}
                  className="py-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  STARS {renderSortArrow('stars')}
                </th>
                <th 
                  onClick={() => handleShortlistSort('1d')}
                  className="py-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  1D {renderSortArrow('1d')}
                </th>
                <th 
                  onClick={() => handleShortlistSort('7d')}
                  className="py-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  7D {renderSortArrow('7d')}
                </th>
                <th 
                  onClick={() => handleShortlistSort('30d')}
                  className="py-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors hidden sm:table-cell"
                >
                  30D {renderSortArrow('30d')}
                </th>
                <th 
                  onClick={() => handleShortlistSort('per_day')}
                  className="py-3 px-4 text-right cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors font-bold text-slate-800 dark:text-slate-200"
                >
                  PER DAY {renderSortArrow('per_day')}
                </th>
                <th 
                  onClick={() => handleShortlistSort('momentum')}
                  className="py-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors hidden md:table-cell"
                >
                  SCORE {renderSortArrow('momentum')}
                </th>
                <th className="py-3 px-3 text-center w-24">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-[#21262d]">
              {sortedShortlist.map((repo, idx) => {
                const initial = (repo.name[0] || 'R').toUpperCase();
                const avatarClass = getAvatarColor(repo.name);

                return (
                  <tr 
                    key={repo.id}
                    onClick={() => onSelectRepository(repo)}
                    className="hover:bg-slate-50 dark:hover:bg-[#1c2128] transition-colors cursor-pointer group"
                  >
                    {/* Rank */}
                    <td className="py-3 px-3 text-center font-mono text-slate-400">
                      {idx + 1}
                    </td>

                    {/* Repository Name & Description */}
                    <td className="py-3 px-4">
                      <div className="flex items-start gap-3">
                        <RepoAvatar owner={repo.owner} name={repo.name} size="md" className="mt-0.5" />
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-mono text-slate-400 text-xs">
                              {repo.owner} /
                            </span>
                            <span className="font-bold text-slate-900 dark:text-white group-hover:text-blue-500 transition-colors">
                              {repo.name}
                            </span>
                          </div>
                          {repo.description && (
                            <p className="text-slate-500 dark:text-slate-400 text-xs line-clamp-1 mt-0.5 max-w-lg font-sans">
                              {repo.description}
                            </p>
                          )}
                          <div className="flex items-center gap-1.5 flex-wrap mt-1">
                            {repo.topics.slice(0, 3).map((t) => (
                              <span 
                                key={t}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onSelectTopic(t);
                                }}
                                className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 dark:bg-[#21262d] text-slate-500 dark:text-slate-400 hover:text-blue-500"
                              >
                                #{t}
                              </span>
                            ))}
                            {repo.language && (
                              <span className="text-[10px] font-mono text-slate-400">
                                • {repo.language}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Stars */}
                    <td className="py-3 px-3 text-right font-mono font-semibold text-slate-800 dark:text-slate-200">
                      {formatStars(repo.stars)}
                    </td>

                    {/* 1D Growth */}
                    <td className="py-3 px-3 text-right font-mono">
                      <span className="inline-block px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 font-semibold">
                        +{repo.growth_1d_pct ?? 0.5}%
                      </span>
                    </td>

                    {/* 7D Growth */}
                    <td className="py-3 px-3 text-right font-mono text-emerald-600 dark:text-emerald-400 font-medium">
                      +{repo.growth_7d_pct ?? 3.5}%
                    </td>

                    {/* 30D Growth */}
                    <td className="py-3 px-3 text-right font-mono text-slate-500 dark:text-slate-400 hidden sm:table-cell">
                      {repo.growth_30d_pct ? `+${repo.growth_30d_pct}%` : '—'}
                    </td>

                    {/* Per Day Velocity */}
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 dark:text-white">
                      +{repo.stars_per_day.toLocaleString()}
                    </td>

                    {/* Composite Momentum Score */}
                    <td className="py-3 px-3 text-right font-mono hidden md:table-cell">
                      <span className="px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 font-semibold text-[11px]">
                        {repo.momentum_score.toFixed(1)}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-3 text-center">
                      <div className="flex items-center justify-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <a
                          href={repo.html_url}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1.5 text-slate-400 hover:text-blue-500 rounded transition-colors"
                          title="Open GitHub"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                        <button
                          onClick={() => onToggleWatchlist(repo.id)}
                          className="p-1.5 text-amber-500 hover:text-slate-400 rounded transition-colors"
                          title="Remove from Shortlist"
                        >
                          <Bookmark className="w-3.5 h-3.5 fill-amber-500" />
                        </button>
                      </div>
                    </td>

                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </main>
    );
  }

  // -------------------------------------------------------------
  // MAIN EXPLORER: TOPIC-SPECIFIC HORIZONTALLY SCROLLABLE ROWS
  // (No redundant top topic bar as user instructed)
  // -------------------------------------------------------------
  
  // If an active topic is selected (e.g. from 904 topics list or tag click)
  if (activeTopic) {
    return (
      <main className="flex-1 overflow-y-auto px-4 lg:px-8 py-5 space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-[#30363d]">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-400">Topic Collection:</span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-blue-600 text-white text-xs font-mono font-medium shadow-sm">
              #{activeTopic}
              <button onClick={() => onSelectTopic(null)} className="hover:opacity-75">
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
            <span className="text-xs font-mono text-slate-400">
              ({repositories.length} repositories)
            </span>
          </div>

          <button
            onClick={() => onSelectTopic(null)}
            className="text-xs font-mono text-blue-500 hover:underline"
          >
            ← Back to all topic rows
          </button>
        </div>

        {/* Repositories grid for this specific topic */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {repositories.map((repo, idx) => (
            <CompactCard
              key={repo.id}
              repo={repo}
              rank={idx + 1}
              onSelectRepository={onSelectRepository}
              onToggleWatchlist={onToggleWatchlist}
              onSelectTopic={onSelectTopic}
            />
          ))}
        </div>

        {/* Load More */}
        <div className="py-6 text-center">
          {hasMore ? (
            <button
              onClick={onLoadMore}
              disabled={isLoading}
              className="px-6 py-2 rounded-xl bg-white dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] text-xs font-mono text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-[#21262d] transition-all shadow-sm flex items-center justify-center gap-2 mx-auto"
            >
              <ChevronDown className="w-4 h-4" />
              <span>{isLoading ? "Loading..." : "Load More"}</span>
            </button>
          ) : (
            <p className="text-xs font-mono text-slate-400">
              Showing all {repositories.length} repositories
            </p>
          )}
        </div>
      </main>
    );
  }

  // Group repositories into topic sections using category top_repositories (25-30 repos each)
  const topicSections = topics.map((cat) => {
    // Sync watchlist state with active repositories
    const repos = (cat.top_repositories || []).map((repo) => {
      const match = repositories.find((r) => r.id === repo.id);
      return match ? { ...repo, is_saved: match.is_saved } : repo;
    });
    return {
      category: cat,
      repositories: repos
    };
  });

  return (
    <main className="flex-1 overflow-y-auto px-4 lg:px-8 py-6 space-y-8">
      
      {/* Topic Rows */}
      {topicSections.map(({ category, repositories: sectionRepos }) => {
        if (!sectionRepos || sectionRepos.length === 0) return null;

        return (
          <TopicScrollSection
            key={category.id}
            category={category}
            repositories={sectionRepos}
            onSelectRepository={onSelectRepository}
            onToggleWatchlist={onToggleWatchlist}
            onSelectTopic={onSelectTopic}
          />
        );
      })}

      {/* General Infinite Scroll Stream of Emerging Breakouts */}
      <div className="pt-4 border-t border-slate-200 dark:border-[#30363d] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Flame className="w-4 h-4 text-amber-500" />
              All Emerging Technology Repositories
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-sans">
              Continuous live stream of ranked GitHub repositories
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {repositories.slice(0, 30).map((repo, idx) => (
            <CompactCard
              key={repo.id}
              repo={repo}
              rank={idx + 1}
              onSelectRepository={onSelectRepository}
              onToggleWatchlist={onToggleWatchlist}
              onSelectTopic={onSelectTopic}
            />
          ))}
        </div>

        <div className="py-4 text-center">
          {hasMore ? (
            <button
              onClick={onLoadMore}
              disabled={isLoading}
              className="px-6 py-2.5 rounded-xl bg-white dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] text-xs font-mono text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-[#21262d] transition-all shadow-sm flex items-center justify-center gap-2 mx-auto"
            >
              <ChevronDown className="w-4 h-4" />
              <span>{isLoading ? "Loading..." : "Load More Repositories"}</span>
            </button>
          ) : (
            <p className="text-xs font-mono text-slate-400">
              Showing all {repositories.length} repositories
            </p>
          )}
        </div>
      </div>

    </main>
  );
};

// -------------------------------------------------------------
// TOPIC HORIZONTAL SCROLL SECTION
// -------------------------------------------------------------
interface TopicScrollSectionProps {
  category: TopicCategory;
  repositories: Repository[];
  onSelectRepository: (repo: Repository) => void;
  onToggleWatchlist: (repoId: number) => void;
  onSelectTopic: (topic: string) => void;
}

const TopicScrollSection: React.FC<TopicScrollSectionProps> = ({
  category,
  repositories,
  onSelectRepository,
  onToggleWatchlist,
  onSelectTopic
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = 600;
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      });
    }
  };

  return (
    <div className="space-y-3 group/section">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
            {category.name}
          </h2>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-[#21262d] text-slate-600 dark:text-slate-400">
            {repositories.length} repos
          </span>
        </div>

        {/* Scroll Nav Buttons & View All */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => scroll('left')}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-[#30363d] bg-white dark:bg-[#161b22] text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors shadow-sm"
            title="Scroll left"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => scroll('right')}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-[#30363d] bg-white dark:bg-[#161b22] text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors shadow-sm"
            title="Scroll right"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Horizontally Scrollable Row Ranking Left to Right */}
      <div
        ref={scrollRef}
        className="flex gap-3.5 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-800"
      >
        {repositories.map((repo, idx) => (
          <div key={repo.id} className="w-[310px] sm:w-[330px] shrink-0">
            <CompactCard
              repo={repo}
              rank={idx + 1}
              onSelectRepository={onSelectRepository}
              onToggleWatchlist={onToggleWatchlist}
              onSelectTopic={onSelectTopic}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

// -------------------------------------------------------------
// COMPACT REPOSITORY CARD
// -------------------------------------------------------------
interface CompactCardProps {
  repo: Repository;
  rank: number;
  onSelectRepository: (repo: Repository) => void;
  onToggleWatchlist: (repoId: number) => void;
  onSelectTopic: (topic: string) => void;
}

const CompactCard: React.FC<CompactCardProps> = ({
  repo,
  rank,
  onSelectRepository,
  onToggleWatchlist,
  onSelectTopic
}) => {
  const initial = (repo.name[0] || 'R').toUpperCase();
  const avatarClass = getAvatarColor(repo.name);

  return (
    <div
      onClick={() => onSelectRepository(repo)}
      className="p-3.5 rounded-xl bg-white dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] hover:border-blue-500/50 dark:hover:border-blue-500/50 transition-all cursor-pointer group flex flex-col justify-between shadow-sm hover:shadow h-full"
    >
      <div>
        {/* Top: Rank, Avatar, Name, Stars & Bookmark */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <RepoAvatar owner={repo.owner} name={repo.name} size="sm" />
            <div className="min-w-0">
              <span className="text-[11px] font-mono text-slate-400 block truncate">
                {repo.owner}
              </span>
              <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-blue-500 transition-colors truncate">
                {repo.name}
              </h4>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-xs font-mono font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-0.5">
              <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
              {formatStars(repo.stars)}
            </span>
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

        {/* Description */}
        <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2 leading-relaxed mb-2.5 font-sans">
          {repo.description || "No description provided."}
        </p>
      </div>

      <div>
        {/* Topic Chips */}
        <div className="flex flex-wrap gap-1 mb-2.5">
          {repo.topics.slice(0, 3).map((t) => (
            <button
              key={t}
              onClick={(e) => {
                e.stopPropagation();
                onSelectTopic(t);
              }}
              className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 dark:bg-[#21262d] text-slate-500 dark:text-slate-400 hover:text-blue-500 hover:bg-slate-200 dark:hover:bg-[#30363d] transition-colors"
            >
              #{t}
            </button>
          ))}
        </div>

        {/* Bottom Metrics Bar */}
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-[#21262d]">
          <div className="flex items-center gap-2">
            <span className="text-emerald-600 dark:text-emerald-400 font-medium">
              +{repo.growth_1d_pct ?? 0.5}% 1d
            </span>
            <span>•</span>
            <span className="text-slate-800 dark:text-slate-200 font-bold">
              +{repo.stars_per_day.toLocaleString()}/day
            </span>
          </div>

          <a
            href={repo.html_url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="p-1 hover:text-blue-500 transition-colors"
            title="Open on GitHub"
          >
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
};
