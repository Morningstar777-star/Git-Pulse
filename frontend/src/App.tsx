import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { SidebarRadar } from './components/SidebarRadar';
import { TopicExplorer } from './components/TopicExplorer';
import { RepositoryModal } from './components/RepositoryModal';
import { TopicsModal } from './components/TopicsModal';
import { 
  fetchRepositories, 
  fetchMomentumRadar, 
  fetchTopics, 
  fetchWatchlist, 
  toggleWatchlist, 
  fetchSystemStatus, 
  triggerRefresh 
} from './services/api';
import { 
  Repository, 
  TopicCategory, 
  SystemStatus, 
  SortMode, 
  TimeWindow, 
  PopularitySortBy 
} from './types';

export const App: React.FC = () => {
  // Navigation & Filter State
  const [mode, setMode] = useState<SortMode>('momentum');
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('7d');
  const [popularitySortBy, setPopularitySortBy] = useState<PopularitySortBy>('stars');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategoryId, setActiveCategoryId] = useState<string | null>(null);
  const [activeTopic, setActiveTopic] = useState<string | null>(null);
  const [isWatchlistView, setIsWatchlistView] = useState(false);

  // Pagination for Infinite Scrolling
  const [repoPage, setRepoPage] = useState(1);
  const [radarPage, setRadarPage] = useState(1);
  const [hasMoreRepos, setHasMoreRepos] = useState(true);
  const [hasMoreRadar, setHasMoreRadar] = useState(true);

  // Data State
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [radarRepositories, setRadarRepositories] = useState<Repository[]>([]);
  const [topics, setTopics] = useState<TopicCategory[]>([]);
  const [watchlist, setWatchlist] = useState<Repository[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  // Modals
  const [selectedRepository, setSelectedRepository] = useState<Repository | null>(null);
  const [isTopicsModalOpen, setIsTopicsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingRadar, setIsLoadingRadar] = useState(false);

  // Load Topics (Curated categories with 30 repos each, sorted by mode)
  const loadTopics = useCallback(async (currentMode: SortMode) => {
    try {
      const topicsData = await fetchTopics(currentMode, 30);
      setTopics(topicsData);
    } catch (err) {
      console.error("Failed to load topics:", err);
    }
  }, []);

  // Load Initial Metadata
  const loadInitialData = useCallback(async () => {
    try {
      const [watchlistData, statusData] = await Promise.all([
        fetchWatchlist(),
        fetchSystemStatus()
      ]);
      setWatchlist(watchlistData);
      setSystemStatus(statusData);
    } catch (err) {
      console.error("Failed to load initial metadata:", err);
    }
  }, []);

  // Load Repositories for Main Content Area (Reset page to 1 on filter change)
  const loadRepositories = useCallback(async (pageToLoad: number = 1, append: boolean = false) => {
    setIsLoading(true);
    try {
      const reposData = await fetchRepositories({
        mode,
        sort_by: popularitySortBy,
        time_window: timeWindow,
        category_id: activeCategoryId || undefined,
        topic: activeTopic || undefined,
        search: searchQuery || undefined,
        watchlist_only: isWatchlistView,
        page: pageToLoad,
        page_size: 40
      });

      if (append) {
        setRepositories((prev) => [...prev, ...reposData]);
      } else {
        setRepositories(reposData);
      }
      setHasMoreRepos(reposData.length >= 40);
    } catch (err) {
      console.error("Failed to load repositories:", err);
    } finally {
      setIsLoading(false);
    }
  }, [mode, popularitySortBy, timeWindow, activeCategoryId, activeTopic, searchQuery, isWatchlistView]);

  // Load Radar Items (for Right Sidebar)
  const loadRadarItems = useCallback(async (pageToLoad: number = 1, append: boolean = false) => {
    setIsLoadingRadar(true);
    try {
      const radarData = await fetchMomentumRadar(timeWindow, pageToLoad, 30);
      if (append) {
        setRadarRepositories((prev) => [...prev, ...radarData]);
      } else {
        setRadarRepositories(radarData);
      }
      setHasMoreRadar(radarData.length >= 30);
    } catch (err) {
      console.error("Failed to load radar repositories:", err);
    } finally {
      setIsLoadingRadar(false);
    }
  }, [timeWindow]);

  // Mount
  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Trigger topics reload on mode change (Momentum vs Popularity)
  useEffect(() => {
    loadTopics(mode);
  }, [mode, loadTopics]);

  // Trigger main repo load on filter change
  useEffect(() => {
    setRepoPage(1);
    const timer = setTimeout(() => {
      loadRepositories(1, false);
    }, 150);
    return () => clearTimeout(timer);
  }, [loadRepositories]);

  // Trigger radar load on timeWindow change
  useEffect(() => {
    setRadarPage(1);
    loadRadarItems(1, false);
  }, [loadRadarItems]);

  // Infinite Scroll: Load More Handlers
  const handleLoadMoreRepos = () => {
    const nextPage = repoPage + 1;
    setRepoPage(nextPage);
    loadRepositories(nextPage, true);
  };

  const handleLoadMoreRadar = () => {
    const nextPage = radarPage + 1;
    setRadarPage(nextPage);
    loadRadarItems(nextPage, true);
  };

  // Watchlist Toggle
  const handleToggleWatchlist = async (repoId: number) => {
    try {
      const res = await toggleWatchlist(repoId);
      
      setRepositories((prev) =>
        prev.map((r) => (r.id === repoId ? { ...r, is_saved: res.is_saved } : r))
      );
      setRadarRepositories((prev) =>
        prev.map((r) => (r.id === repoId ? { ...r, is_saved: res.is_saved } : r))
      );
      if (selectedRepository && selectedRepository.id === repoId) {
        setSelectedRepository({ ...selectedRepository, is_saved: res.is_saved });
      }

      const updatedWatchlist = await fetchWatchlist();
      setWatchlist(updatedWatchlist);
    } catch (err) {
      console.error("Failed to toggle watchlist:", err);
    }
  };

  // Manual Trigger Refresh
  const handleTriggerRefresh = async () => {
    try {
      await triggerRefresh();
      const updatedStatus = await fetchSystemStatus();
      setSystemStatus(updatedStatus);
      setTimeout(() => {
        loadRepositories(1, false);
        loadRadarItems(1, false);
      }, 1500);
    } catch (err) {
      console.error("Refresh trigger error:", err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0d1117] text-slate-900 dark:text-[#e6edf3] flex flex-col transition-colors duration-200">
      
      {/* Top Global Navigation Bar */}
      <Header
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        mode={mode}
        onModeChange={setMode}
        timeWindow={timeWindow}
        onTimeWindowChange={setTimeWindow}
        popularitySortBy={popularitySortBy}
        onPopularitySortChange={setPopularitySortBy}
        watchlistCount={watchlist.length}
        isWatchlistActive={isWatchlistView}
        onToggleWatchlistView={() => setIsWatchlistView(!isWatchlistView)}
        onOpenTopicsModal={() => setIsTopicsModalOpen(true)}
        totalTopicsCount={systemStatus?.total_topics || 904}
        systemStatus={systemStatus}
        onTriggerRefresh={handleTriggerRefresh}
      />

      {/* Main Cockpit Split Layout: Left/Center Main Explorer + Right Side Momentum Radar */}
      <div className="flex-1 flex flex-col xl:flex-row max-w-[1720px] w-full mx-auto">
        
        {/* Left/Center Main Content Area */}
        <TopicExplorer
          repositories={isWatchlistView ? watchlist : repositories}
          topics={topics}
          activeCategoryId={activeCategoryId}
          activeTopic={activeTopic}
          onSelectCategory={(catId) => {
            setActiveCategoryId(catId);
            setActiveTopic(null);
          }}
          onSelectTopic={(topic) => {
            setActiveTopic(topic);
            setActiveCategoryId(null);
          }}
          onSelectRepository={(repo) => setSelectedRepository(repo)}
          onToggleWatchlist={handleToggleWatchlist}
          isShortlistView={isWatchlistView}
          onLoadMore={handleLoadMoreRepos}
          hasMore={hasMoreRepos}
          isLoading={isLoading}
          sortMode={mode}
        />

        {/* Right Sidebar: Momentum Radar (Placed on Right Side) */}
        {!isWatchlistView && (
          <SidebarRadar
            repositories={radarRepositories}
            timeWindow={timeWindow}
            onSelectRepository={(repo) => setSelectedRepository(repo)}
            onToggleWatchlist={handleToggleWatchlist}
            onSelectTopic={(topic) => {
              setActiveTopic(topic);
              setActiveCategoryId(null);
            }}
            onLoadMore={handleLoadMoreRadar}
            hasMore={hasMoreRadar}
            isLoading={isLoadingRadar}
          />
        )}

      </div>

      {/* Repository Detail Modal */}
      <RepositoryModal
        repository={selectedRepository}
        onClose={() => setSelectedRepository(null)}
        onToggleWatchlist={handleToggleWatchlist}
        onSelectRelated={(repo) => setSelectedRepository(repo)}
        onSelectTopic={(topic) => {
          setActiveTopic(topic);
          setActiveCategoryId(null);
        }}
      />

      {/* All Topics Directory Modal (900+ Topics) */}
      <TopicsModal
        isOpen={isTopicsModalOpen}
        onClose={() => setIsTopicsModalOpen(false)}
        selectedTopic={activeTopic}
        onSelectTopic={(topic) => {
          setActiveTopic(topic);
          setActiveCategoryId(null);
        }}
      />

    </div>
  );
};
