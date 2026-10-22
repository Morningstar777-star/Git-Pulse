import React, { useEffect, useState } from 'react';
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
  Clock,
  TrendingUp,
  Code
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

export const RepositoryModal: React.FC<RepositoryModalProps> = ({
  repository,
  onClose,
  onToggleWatchlist,
  onSelectRelated,
  onSelectTopic
}) => {
  const [detail, setDetail] = useState<RepositoryDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!repository) {
      setDetail(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    fetchRepositoryDetail(repository.id)
      .then((data) => {
        if (isMounted) setDetail(data);
      })
      .catch((err) => console.error("Failed to load repo detail:", err))
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => { isMounted = false; };
  }, [repository]);

  if (!repository) return null;

  const repo = detail || (repository as unknown as RepositoryDetail);

  // Clean and deduplicate snapshots chronologically (latest per date)
  const cleanSnapshots = React.useMemo(() => {
    if (!repo.snapshots || repo.snapshots.length === 0) return [];
    const byDate = new Map<string, SparklinePoint>();
    for (const s of repo.snapshots) {
      const d = s.date.slice(0, 10);
      byDate.set(d, s);
    }
    const uniqueList = Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
    return uniqueList.slice(-12);
  }, [repo.snapshots]);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto bg-black/60 dark:bg-black/85 backdrop-blur-md animate-in fade-in duration-200"
      onClick={onClose}
    >
      {/* Modal Dialog Card */}
      <div 
        className="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] shadow-2xl p-6 sm:p-8 space-y-6 max-h-[90vh] overflow-y-auto text-slate-900 dark:text-[#e6edf3]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 dark:border-[#30363d] pb-5">
          <div className="flex items-start gap-3.5">
            <RepoAvatar owner={repo.owner} name={repo.name} size="lg" />
            <div>
              <div className="flex items-center gap-1.5 font-mono text-xs text-slate-400 dark:text-slate-500">
                <span>{repo.owner}</span>
                <span>/</span>
                {repo.language && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-[#21262d] text-slate-600 dark:text-slate-300">
                    <Code className="w-2.5 h-2.5" />
                    {repo.language}
                  </span>
                )}
              </div>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white mt-0.5">
                {repo.name}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onToggleWatchlist(repo.id)}
              className={`p-2.5 rounded-xl border transition-all flex items-center gap-1.5 text-xs font-mono font-medium ${
                repo.is_saved
                  ? 'bg-amber-500 text-white border-amber-600 shadow-sm'
                  : 'bg-slate-100 dark:bg-[#21262d] border-slate-200 dark:border-[#30363d] text-slate-600 dark:text-slate-400 hover:text-amber-500'
              }`}
              title={repo.is_saved ? "Remove from Shortlist" : "Add to Shortlist"}
            >
              <Bookmark className={`w-4 h-4 ${repo.is_saved ? 'fill-white' : ''}`} />
              <span className="hidden sm:inline">
                {repo.is_saved ? 'Shortlisted' : 'Shortlist'}
              </span>
            </button>

            <a
              href={repo.html_url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-mono font-medium transition-all shadow-sm"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>

            <button
              onClick={onClose}
              className="p-2.5 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Description */}
        <div className="space-y-1">
          <p className="text-sm text-slate-700 dark:text-slate-200 font-sans leading-relaxed">
            {repo.description || "No description provided."}
          </p>
        </div>

        {/* Telemetry Stat Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#0d1117] border border-slate-200 dark:border-[#21262d] space-y-1">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
              <Star className="w-3 h-3 text-amber-500 fill-amber-500" /> Total Stars
            </span>
            <p className="text-xl font-bold font-mono text-slate-900 dark:text-white">
              {repo.stars.toLocaleString()}
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#0d1117] border border-slate-200 dark:border-[#21262d] space-y-1">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-emerald-500" /> Per Day
            </span>
            <p className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              +{repo.stars_per_day.toLocaleString()}
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#0d1117] border border-slate-200 dark:border-[#21262d] space-y-1">
            <span className="text-[11px] text-slate-400 font-mono">
              1D Growth
            </span>
            <p className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              +{repo.growth_1d_pct ?? 0.5}%
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#0d1117] border border-slate-200 dark:border-[#21262d] space-y-1">
            <span className="text-[11px] text-slate-400 font-mono">
              7D Growth
            </span>
            <p className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              +{repo.growth_7d_pct ?? 3.5}%
            </p>
          </div>
        </div>

        {/* Observed Star Growth Chart */}
        <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#0d1117] border border-slate-200 dark:border-[#21262d] space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 dark:text-white font-mono flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-blue-500" />
              Historical Star Trajectory
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              {cleanSnapshots.length} Day Snapshots Logged
            </span>
          </div>

          {cleanSnapshots.length > 1 ? (
            <div className="pt-2 w-full overflow-hidden">
              <div className="h-32 w-full flex items-end gap-1.5 sm:gap-2 border-b border-l border-slate-200 dark:border-[#30363d] px-2 pb-2">
                {cleanSnapshots.map((snap, i) => {
                  const min = Math.min(...cleanSnapshots.map(s => s.stars));
                  const max = Math.max(...cleanSnapshots.map(s => s.stars));
                  const heightPercent = Math.max(15, ((snap.stars - min) / (max - min || 1)) * 100);

                  return (
                    <div key={i} className="flex-1 min-w-0 flex flex-col items-center h-full justify-end group relative">
                      {/* Tooltip positioned absolutely above */}
                      <div className="absolute -top-7 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] font-mono text-slate-800 dark:text-slate-200 whitespace-nowrap bg-white dark:bg-black px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-800 shadow-md pointer-events-none z-10">
                        {snap.stars.toLocaleString()}
                      </div>
                      <div 
                        className="w-full max-w-[36px] rounded-t-sm bg-blue-500 group-hover:bg-blue-400 transition-all cursor-pointer"
                        style={{ height: `${heightPercent}%` }}
                      />
                      <span className="text-[9px] font-mono text-slate-400 truncate w-full text-center mt-1">
                        {snap.date.slice(5)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="py-6 text-center text-xs font-mono text-slate-400">
              Collecting continuous daily snapshots over automatic background sync cycles.
            </div>
          )}
        </div>

        {/* Topics / Tags */}
        {repo.topics && repo.topics.length > 0 && (
          <div className="space-y-2">
            <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-slate-400" /> Topics
            </span>
            <div className="flex flex-wrap gap-1.5">
              {repo.topics.map((t, idx) => (
                <button 
                  key={idx} 
                  onClick={() => {
                    onSelectTopic(t);
                    onClose();
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-[#21262d] hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-500 border border-slate-200 dark:border-[#30363d] text-slate-700 dark:text-slate-300 text-xs font-mono transition-colors"
                >
                  #{t}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Related Repositories in this Category */}
        {repo.related_repositories && repo.related_repositories.length > 0 && (
          <div className="border-t border-slate-200 dark:border-[#30363d] pt-4 space-y-2.5">
            <h4 className="text-xs font-mono text-slate-400">
              Related Emerging Repositories
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {repo.related_repositories.map((rel) => (
                <div
                  key={rel.id}
                  onClick={() => onSelectRelated(rel)}
                  className="p-3 rounded-xl bg-slate-50 dark:bg-[#0d1117] hover:bg-slate-100 dark:hover:bg-[#21262d] border border-slate-200 dark:border-[#21262d] cursor-pointer transition-all flex items-center justify-between"
                >
                  <div className="min-w-0 pr-2">
                    <h5 className="text-xs font-bold text-slate-900 dark:text-white truncate">
                      {rel.name}
                    </h5>
                    <span className="text-[11px] text-slate-400 font-mono">
                      ★ {rel.stars.toLocaleString()} • {rel.language || 'Code'}
                    </span>
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-slate-400 shrink-0" />
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
