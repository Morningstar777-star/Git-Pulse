import React, { useEffect, useState, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { 
  X, 
  ExternalLink, 
  Star, 
  GitFork, 
  Flame, 
  Bookmark, 
  Activity, 
  Tag, 
  ArrowUpRight, 
  TrendingUp, 
  Code,
  ShieldCheck,
  Calendar
} from 'lucide-react';
import { Repository, RepositoryDetail, SparklinePoint } from '../types';
import { fetchRepositoryDetail } from '../services/api';
import { RepoAvatar } from './RepoAvatar';

interface RepositoryModalProps {
  repository: Repository | null;
  onClose: () => void;
  onToggleWatchlist: (repoId: number) => void;
  onSelectRelated: (repo: Repository) => void;
  onSelectTopic: (topic: string) => void;
}

export const RepositoryModal: React.FC<RepositoryModalProps> = ({
  repository,
  onClose,
  onToggleWatchlist,
  onSelectRelated,
  onSelectTopic
}) => {
  const [detail, setDetail] = useState<RepositoryDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showOriginal, setShowOriginal] = useState(false);

  // Close on Escape key & lock body scroll while modal is mounted
  useEffect(() => {
    if (!repository) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    window.addEventListener('keydown', handleKeyDown);
    const origOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = origOverflow;
    };
  }, [repository, onClose]);

  // Fetch full detail when repository changes
  useEffect(() => {
    if (!repository?.id) {
      setDetail(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setDetail(null);

    fetchRepositoryDetail(repository.id)
      .then((data) => {
        if (isMounted) setDetail(data);
      })
      .catch((err) => {
        console.error("Failed to load repo detail:", err);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [repository?.id]);

  // Clean and deduplicate snapshots chronologically
  const activeRepo = detail || (repository as unknown as RepositoryDetail);

  const cleanSnapshots = useMemo(() => {
    if (!activeRepo?.snapshots || !Array.isArray(activeRepo.snapshots) || activeRepo.snapshots.length === 0) {
      return [];
    }
    const byDate = new Map<string, SparklinePoint>();
    for (const s of activeRepo.snapshots) {
      if (s && s.date) {
        const d = String(s.date).slice(0, 10);
        byDate.set(d, {
          date: d,
          stars: Number(s.stars) || 0
        });
      }
    }
    return Array.from(byDate.values())
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-14);
  }, [activeRepo?.snapshots]);

  if (!repository) return null;

  const repo = activeRepo;
  const starsFormatted = (repo?.stars ?? 0).toLocaleString();
  const perDayFormatted = (repo?.stars_per_day ?? 0).toLocaleString();
  const growth1d = repo?.growth_1d_pct ?? 0.0;
  const growth7d = repo?.growth_7d_pct ?? 0.0;
  const forksFormatted = (repo?.forks ?? 0).toLocaleString();
  const issuesFormatted = (repo?.open_issues ?? 0).toLocaleString();
  const topicsList = Array.isArray(repo?.topics) ? repo.topics : [];
  const relatedList = Array.isArray(repo?.related_repositories) ? repo.related_repositories : [];

  const modalContent = (
    <div 
      className="fixed inset-0 z-[99999] flex items-center justify-center p-3 sm:p-6 overflow-y-auto bg-black/75 dark:bg-black/90 backdrop-blur-md transition-opacity animate-in fade-in duration-150"
      onClick={onClose}
    >
      {/* Modal Dialog Card */}
      <div 
        className="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-[#12171f] border border-slate-200 dark:border-[#2a3241] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.7)] p-5 sm:p-7 space-y-6 max-h-[92vh] overflow-y-auto text-slate-900 dark:text-[#e6edf3]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-start justify-between gap-4 border-b border-slate-200/80 dark:border-[#21262d] pb-4">
          <div className="flex items-start gap-3.5 min-w-0">
            <RepoAvatar owner={repo.owner} name={repo.name} size="lg" className="shrink-0 mt-0.5" />
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 font-mono text-xs text-slate-400 dark:text-slate-400 truncate">
                <span>{repo.owner}</span>
                <span>/</span>
                {repo.language && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-[#1c222c] text-slate-700 dark:text-slate-300 font-medium">
                    <Code className="w-2.5 h-2.5 text-blue-500" />
                    {repo.language}
                  </span>
                )}
                {repo.momentum_score && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 font-bold border border-amber-500/20">
                    <Flame className="w-2.5 h-2.5 fill-amber-500 text-amber-500" />
                    {repo.momentum_score.toFixed(1)} BKM
                  </span>
                )}
              </div>
              <a
                href={repo.html_url || `https://github.com/${repo.full_name}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white hover:text-blue-500 hover:underline transition-colors mt-1 truncate block"
                title={`Open ${repo.full_name} on GitHub`}
              >
                {repo.name}
              </a>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => onToggleWatchlist(repo.id)}
              className={`px-3 py-2 rounded-xl border transition-all flex items-center gap-1.5 text-xs font-mono font-medium ${
                repo.is_saved
                  ? 'bg-amber-500 text-white border-amber-600 shadow-sm'
                  : 'bg-slate-100 dark:bg-[#1c222c] border-slate-200 dark:border-[#30363d] text-slate-700 dark:text-slate-300 hover:text-amber-500'
              }`}
              title={repo.is_saved ? "Remove from Shortlist" : "Add to Shortlist"}
            >
              <Bookmark className={`w-3.5 h-3.5 ${repo.is_saved ? 'fill-white' : ''}`} />
              <span className="hidden sm:inline">
                {repo.is_saved ? 'Shortlisted' : 'Shortlist'}
              </span>
            </button>

            <a
              href={repo.html_url || `https://github.com/${repo.full_name}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-mono font-medium transition-all shadow-sm"
              title="Open repository on GitHub"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Close modal (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Description & Native Translation Pill */}
        <div className="space-y-1.5">
          <p className="text-sm text-slate-700 dark:text-slate-300 font-sans leading-relaxed">
            {Boolean(repo.description_en && repo.description_en !== repo.description)
              ? (showOriginal ? repo.description : repo.description_en)
              : (repo.description || "No description provided for this repository.")}
          </p>
          {Boolean(repo.description_en && repo.description_en !== repo.description) && (
            <button
              type="button"
              onClick={() => setShowOriginal(!showOriginal)}
              className="inline-flex items-center gap-1 text-xs font-mono text-blue-600 dark:text-blue-400 hover:underline"
            >
              <span>🌐 {showOriginal ? "Show English Translation" : "Translated from original CJK text"}</span>
              <span className="text-slate-400">({showOriginal ? "原文" : "Original"})</span>
            </button>
          )}
        </div>

        {/* Telemetry Stat Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#0a0e14] border border-slate-200 dark:border-[#1f2530] space-y-1">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
              <Star className="w-3 h-3 text-amber-500 fill-amber-500" /> Total Stars
            </span>
            <p className="text-xl font-bold font-mono text-slate-900 dark:text-white">
              {starsFormatted}
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#0a0e14] border border-slate-200 dark:border-[#1f2530] space-y-1">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-emerald-500" /> Velocity
            </span>
            <p className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              +{perDayFormatted}/day
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#0a0e14] border border-slate-200 dark:border-[#1f2530] space-y-1">
            <span className="text-[11px] text-slate-400 font-mono">
              1D Momentum
            </span>
            <p className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              +{growth1d}%
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#0a0e14] border border-slate-200 dark:border-[#1f2530] space-y-1">
            <span className="text-[11px] text-slate-400 font-mono">
              7D Momentum
            </span>
            <p className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              +{growth7d}%
            </p>
          </div>
        </div>

        {/* Observed Star Growth Chart */}
        <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#0a0e14] border border-slate-200 dark:border-[#1f2530] space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 dark:text-white font-mono flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-blue-500" />
              Observed Star History
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              {cleanSnapshots.length > 0 ? `${cleanSnapshots.length} Snapshot Logs` : 'Logging Data Points'}
            </span>
          </div>

          {cleanSnapshots.length > 1 ? (
            <div className="pt-2 w-full overflow-hidden">
              <div className="h-32 w-full flex items-end gap-1.5 sm:gap-2 border-b border-l border-slate-200 dark:border-[#2a3241] px-2 pb-2">
                {(() => {
                  const starsArr = cleanSnapshots.map((s) => s.stars);
                  const min = Math.min(...starsArr);
                  const max = Math.max(...starsArr);
                  const range = max - min || 1;

                  return cleanSnapshots.map((snap, i) => {
                    const heightPercent = Math.max(18, ((snap.stars - min) / range) * 100);

                    return (
                      <div key={i} className="flex-1 min-w-0 flex flex-col items-center h-full justify-end group relative">
                        {/* Tooltip */}
                        <div className="absolute -top-7 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] font-mono text-slate-800 dark:text-slate-200 whitespace-nowrap bg-white dark:bg-black px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-800 shadow-md pointer-events-none z-10">
                          {snap.stars.toLocaleString()}
                        </div>
                        <div 
                          className="w-full max-w-[36px] rounded-t-sm bg-gradient-to-t from-blue-600 to-cyan-400 group-hover:to-cyan-300 transition-all cursor-pointer"
                          style={{ height: `${heightPercent}%` }}
                        />
                        <span className="text-[9px] font-mono text-slate-400 truncate w-full text-center mt-1">
                          {snap.date ? snap.date.slice(5) : ''}
                        </span>
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          ) : (
            <div className="py-6 text-center text-xs font-mono text-slate-400">
              {isLoading ? "Fetching chronological telemetry snapshots..." : "Tracking telemetry over automated hourly crawler background cycles."}
            </div>
          )}
        </div>

        {/* Topics / Tags */}
        {topicsList.length > 0 && (
          <div className="space-y-2">
            <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-slate-400" /> Topics & Domain Keywords
            </span>
            <div className="flex flex-wrap gap-1.5">
              {topicsList.map((t, idx) => (
                <button 
                  key={idx} 
                  onClick={() => {
                    onSelectTopic(t);
                    onClose();
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-[#1a202c] hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-500 border border-slate-200 dark:border-[#2d3748] text-slate-700 dark:text-slate-300 text-xs font-mono transition-colors"
                >
                  #{t}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Related Repositories in this Category */}
        {relatedList.length > 0 && (
          <div className="border-t border-slate-200/80 dark:border-[#21262d] pt-4 space-y-2.5">
            <h4 className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-cyan-500" />
              Related Repositories in Same Category
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {relatedList.map((rel) => (
                <div
                  key={rel.id}
                  onClick={() => onSelectRelated(rel)}
                  className="p-3 rounded-xl bg-slate-50 dark:bg-[#0a0e14] hover:bg-slate-100 dark:hover:bg-[#1a202c] border border-slate-200 dark:border-[#1f2530] hover:border-blue-500/40 cursor-pointer transition-all flex items-center justify-between group"
                >
                  <div className="min-w-0 pr-2">
                    <h5 className="text-xs font-bold text-slate-900 dark:text-white truncate group-hover:text-blue-500 transition-colors">
                      {rel.name}
                    </h5>
                    <span className="text-[11px] text-slate-400 font-mono">
                      ★ {(rel?.stars ?? 0).toLocaleString()} • {rel.language || 'Code'}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <a
                      href={rel.html_url || `https://github.com/${rel.full_name}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="p-1 text-slate-400 hover:text-blue-500 transition-colors"
                      title="Open on GitHub"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                    <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};
