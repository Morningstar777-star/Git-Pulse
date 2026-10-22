import React, { useState, useEffect } from 'react';
import { X, Search, Hash, Tag, Filter } from 'lucide-react';
import { TopicItem } from '../types';
import { fetchAllTopics } from '../services/api';

interface TopicsModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedTopic: string | null;
  onSelectTopic: (topic: string | null) => void;
}

export const TopicsModal: React.FC<TopicsModalProps> = ({
  isOpen,
  onClose,
  selectedTopic,
  onSelectTopic
}) => {
  const [topics, setTopics] = useState<TopicItem[]>([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setIsLoading(true);
    fetchAllTopics('', 800)
      .then((data) => setTopics(data))
      .catch((err) => console.error("Failed to fetch topics:", err))
      .finally(() => setIsLoading(false));
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredTopics = topics.filter((t) =>
    t.topic.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 dark:bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div 
        className="relative w-full max-w-4xl rounded-2xl bg-white dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] shadow-2xl p-6 space-y-5 max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-[#30363d] pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
              <Hash className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
                All Topics Directory
                <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-900">
                  {topics.length} Indexed
                </span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Browse and filter across all discovered technologies and tags
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search input */}
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter topics (e.g. rust, llm, react, cordis, agent)..."
            className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 dark:bg-[#0d1117] border border-slate-200 dark:border-[#30363d] rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition-all font-sans"
            autoFocus
          />
        </div>

        {/* Selected Topic Pill if active */}
        {selectedTopic && (
          <div className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 text-xs text-blue-700 dark:text-blue-300">
            <span>Currently filtering by: <strong>#{selectedTopic}</strong></span>
            <button
              onClick={() => {
                onSelectTopic(null);
                onClose();
              }}
              className="text-xs font-semibold hover:underline"
            >
              Clear filter
            </button>
          </div>
        )}

        {/* Topics Cloud / Grid */}
        <div className="flex-1 overflow-y-auto pr-1">
          {isLoading && (
            <div className="py-12 text-center text-xs font-mono text-slate-400">
              Loading topic index...
            </div>
          )}

          {!isLoading && filteredTopics.length === 0 && (
            <div className="py-12 text-center text-xs font-mono text-slate-400">
              No matching topics found for "{search}".
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            {!isLoading && filteredTopics.map((t) => {
              const isSelected = selectedTopic === t.topic;
              return (
                <button
                  key={t.topic}
                  onClick={() => {
                    onSelectTopic(isSelected ? null : t.topic);
                    onClose();
                  }}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                    isSelected
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'bg-slate-100 dark:bg-[#21262d] text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-[#30363d] border border-slate-200 dark:border-transparent'
                  }`}
                >
                  <span className="text-slate-400 dark:text-slate-500">#</span>
                  <span>{t.topic}</span>
                  <span className={`text-[10px] font-mono px-1 rounded ${
                    isSelected ? 'bg-blue-700 text-white' : 'bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                  }`}>
                    {t.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-slate-200 dark:border-[#30363d] pt-3 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-mono">
          <span>Showing {filteredTopics.length} of {topics.length} topics</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
