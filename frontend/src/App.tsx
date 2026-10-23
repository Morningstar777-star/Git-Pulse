import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { SidebarRadar } from './components/SidebarRadar';
import { TopicExplorer } from './components/TopicExplorer';
import { RepositoryModal } from './components/RepositoryModal';
import { TopicsModal } from './components/TopicsModal';
import { AuthModal } from './components/AuthModal';
import { 
  fetchRepositories, 
  fetchMomentumRadar, 
  fetchTopics, 
  fetchWatchlist, 
  toggleWatchlist, 
  fetchSystemStatus, 
  triggerRefresh,
  fetchMe,
  signOut
} from './services/api';
import { 
  Repository, 
  TopicCategory, 
  SystemStatus, 
  SortMode, 
  TimeWindow, 
  PopularitySortBy,
  User
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

  // Modals & User Auth State
  const [user, setUser] = useState<User | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalReason, setAuthModalReason] = useState<string | null>(null);
  const [selectedRepository, setSelectedRepository] = useState<Repository | null>(null);
  const [isTopicsModalOpen, setIsTopicsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingRadar, setIsLoadingRadar] = useState(false);

  // Load Topics (Curated categories with 30 repos each, sorted by mode and timeframe)
  const loadTopics = useCallback(async (currentMode: SortMode, currentTimeWindow: TimeWindow) => {
    try {
      const topicsData = await fetchTopics(currentMode, currentTimeWindow, 30);
      setTopics(topicsData);
    } catch (err) {
      console.error("Failed to load topics:", err);
    }
  }, []);

  // Load Initial Metadata & User Session
  const loadInitialData = useCallback(async () => {
    try {
      const [currentUser, statusData] = await Promise.all([
        fetchMe(),
        fetchSystemStatus()
      ]);
      setUser(currentUser);
      setSystemStatus(statusData);

      if (currentUser) {
        const watchlistData = await fetchWatchlist();
        setWatchlist(watchlistData);
      } else {
        setWatchlist([]);
      }
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

  // Trigger topics reload on mode OR timeWindow change
  useEffect(() => {
    loadTopics(mode, timeWindow);
  }, [mode, timeWindow, loadTopics]);

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
    if (!user) {
      setAuthModalReason("Sign in to save repositories to your personal watchlist.");
      setIsAuthModalOpen(true);
      return;
    }

    try {
      const res = await toggleWatchlist(repoId);
      
      setRepositories((prev) =>
        prev.map((r) => (r.id === repoId ? { ...r, is_saved: res.is_saved } : r))
      );
      setRadarRepositories((prev) =>
        prev.map((r) => (r.id === repoId ? { ...r, is_saved: res.is_saved } : r))
      );
      setTopics((prev) =>
        prev.map((cat) => ({
          ...cat,
          top_repositories: (cat.top_repositories || []).map((r) =>
            r.id === repoId ? { ...r, is_saved: res.is_saved } : r
          )
        }))
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

  // Auth Handlers
  const handleSignOut = async () => {
    await signOut();
    setUser(null);
    setWatchlist([]);
    setRepositories((prev) => prev.map((r) => ({ ...r, is_saved: false })));
    setRadarRepositories((prev) => prev.map((r) => ({ ...r, is_saved: false })));
    setTopics((prev) =>
      prev.map((cat) => ({
        ...cat,
        top_repositories: (cat.top_repositories || []).map((r) => ({ ...r, is_saved: false }))
      }))
    );
    if (isWatchlistView) {
      setIsWatchlistView(false);
    }
  };

  const handleAuthSuccess = async (authenticatedUser: User) => {
    setUser(authenticatedUser);
    setIsAuthModalOpen(false);
    setAuthModalReason(null);
    try {
      const watchlistData = await fetchWatchlist();
      setWatchlist(watchlistData);
      const savedIds = new Set(watchlistData.map((r) => r.id));
      setRepositories((prev) =>
        prev.map((r) => ({ ...r, is_saved: savedIds.has(r.id) }))
      );
      setRadarRepositories((prev) =>
        prev.map((r) => ({ ...r, is_saved: savedIds.has(r.id) }))
      );
      setTopics((prev) =>
        prev.map((cat) => ({
          ...cat,
          top_repositories: (cat.top_repositories || []).map((r) => ({
            ...r,
            is_saved: savedIds.has(r.id)
          }))
        }))
      );
    } catch (err) {
      console.error("Failed to refresh watchlist after auth:", err);
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
        onToggleWatchlistView={() => {
          if (!user && !isWatchlistView) {
            setAuthModalReason("Sign in to access and manage your personal saved watchlist.");
            setIsAuthModalOpen(true);
            return;
          }
          setIsWatchlistView(!isWatchlistView);
        }}
        onOpenTopicsModal={() => setIsTopicsModalOpen(true)}
        totalTopicsCount={systemStatus?.total_topics || 904}
        systemStatus={systemStatus}
        onTriggerRefresh={handleTriggerRefresh}
        user={user}
        onOpenAuthModal={() => {
          setAuthModalReason(null);
          setIsAuthModalOpen(true);
        }}
        onSignOut={handleSignOut}
      />

      {/* Main Cockpit Split Layout: Left/Center Main Explorer + Right Side Momentum Radar */}
      <div className="flex-1 flex flex-col xl:flex-row max-w-[1720px] w-full mx-auto">
        
        {/* Left/Center Main Content Area */}
        <TopicExplorer
          repositories={isWatchlistView ? watchlist : repositories}
          topics={topics}
          activeCategoryId={activeCategoryId}
          activeTopic={activeTopic}
          searchQuery={searchQuery}
          onClearSearch={() => setSearchQuery('')}
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

      {/* User Authentication & Password Recovery Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => {
          setIsAuthModalOpen(false);
          setAuthModalReason(null);
        }}
        onAuthSuccess={handleAuthSuccess}
        reason={authModalReason}
      />

    </div>
  );
};
