import React, { useState } from 'react';
import { 
  Search, Plus, Grid, List, Filter, Settings, BookOpen, Download, 
  Heart, Star, MoreHorizontal, ChevronLeft, ChevronRight, FileText, 
  Tag, Menu, X, Home, Library, Users, TrendingUp, Clock, Bookmark
} from 'lucide-react';

// Mock data
const mockSeries = [
  {
    id: 1,
    title: "Attack on Titan",
    author: "Hajime Isayama",
    status: "Completed",
    genres: ["Action", "Drama", "Fantasy"],
    cover: "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=600&fit=crop",
    chapters: 139,
    readChapters: 89,
    description: "Humanity fights for survival against giant humanoid Titans...",
    rating: 4.8,
    tags: ["Must Read", "Finished"],
    trending: true,
    lastRead: "2 days ago"
  },
  {
    id: 2,
    title: "One Piece",
    author: "Eiichiro Oda",
    status: "Ongoing",
    genres: ["Action", "Adventure", "Comedy"],
    cover: "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=600&fit=crop",
    chapters: 1095,
    readChapters: 1032,
    description: "Follow Monkey D. Luffy's journey to become the Pirate King...",
    rating: 4.9,
    tags: ["Currently Reading"],
    newChapters: 3,
    lastRead: "Today"
  },
  {
    id: 3,
    title: "Demon Slayer",
    author: "Koyoharu Gotouge",
    status: "Completed",
    genres: ["Action", "Supernatural"],
    cover: "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=600&fit=crop",
    chapters: 205,
    readChapters: 0,
    description: "Tanjiro's quest to turn his demon sister back to human...",
    rating: 4.7,
    tags: ["To Read"],
    isNew: true
  }
];

const mockChapters = [
  { id: 1, number: 1, title: "To You, 2000 Years From Now", read: true, downloaded: true },
  { id: 2, number: 2, title: "That Day", read: true, downloaded: true },
  { id: 3, number: 3, title: "A Dim Light in the Darkness", read: false, downloaded: false },
];

const mockLists = [
  { id: 1, name: "Currently Reading", count: 12, color: "bg-blue-500", emoji: "📖" },
  { id: 2, name: "Must Read", count: 8, color: "bg-red-500", emoji: "⭐" },
  { id: 3, name: "Completed", count: 45, color: "bg-green-500", emoji: "✅" },
  { id: 4, name: "To Read", count: 23, color: "bg-purple-500", emoji: "📚" }
];

const KireMisuApp = () => {
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedSeries, setSelectedSeries] = useState(null);
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [viewMode, setViewMode] = useState('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [showAnnotation, setShowAnnotation] = useState(false);
  const [annotation, setAnnotation] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Navigation items
  const navigationItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Home },
    { id: 'library', label: 'Library', icon: Library },
    { id: 'lists', label: 'Lists', icon: Heart },
    { id: 'downloads', label: 'Downloads', icon: Download },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  // Modern Button Component
  const Button = ({ children, onClick, className = "", variant = "default", size = "default" }) => {
    let baseStyles = "rounded-xl font-medium transition-all duration-200 flex items-center justify-center ";
    
    if (size === "sm") {
      baseStyles += "px-3 py-1.5 text-sm ";
    } else if (size === "lg") {
      baseStyles += "px-6 py-3 text-base ";
    } else {
      baseStyles += "px-4 py-2.5 text-sm ";
    }
    
    if (variant === "default") {
      baseStyles += "bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 ";
    } else if (variant === "ghost") {
      baseStyles += "text-slate-300 hover:bg-slate-800/50 hover:text-orange-400 ";
    } else if (variant === "outline") {
      baseStyles += "border border-slate-700/50 bg-slate-900/50 backdrop-blur-sm text-white hover:bg-slate-800/50 hover:border-orange-500/50 ";
    } else if (variant === "glass") {
      baseStyles += "bg-white/10 backdrop-blur-md border border-white/20 text-white hover:bg-white/20 ";
    }
    
    return (
      <button className={baseStyles + className} onClick={onClick}>
        {children}
      </button>
    );
  };

  // Modern Input Component
  const Input = ({ placeholder, value, onChange, className = "", icon }) => (
    <div className="relative">
      {icon && (
        <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400">
          {icon}
        </div>
      )}
      <input
        className={`w-full px-4 py-3 bg-slate-900/50 backdrop-blur-sm border border-slate-700/50 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all ${icon ? 'pl-10' : ''} ${className}`}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
      />
    </div>
  );

  // Modern Card Component
  const Card = ({ children, className = "", onClick, gradient = false }) => (
    <div 
      className={`bg-slate-900/60 backdrop-blur-sm border border-slate-800/50 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 ${gradient ? 'bg-gradient-to-br from-slate-900/80 to-slate-800/60' : ''} ${onClick ? 'cursor-pointer hover:scale-[1.02] hover:-translate-y-1' : ''} ${className}`} 
      onClick={onClick}
    >
      {children}
    </div>
  );

  // Stats Card Component
  const StatsCard = ({ title, value, change, icon, color = "text-orange-400" }) => (
    <Card className="p-6" gradient>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-slate-400 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          {change && (
            <p className={`text-sm mt-1 ${change.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>
              {change} from last week
            </p>
          )}
        </div>
        <div className={`p-3 rounded-xl bg-slate-800/50 ${color}`}>
          {icon}
        </div>
      </div>
    </Card>
  );

  // Mobile Navigation
  const MobileNav = () => {
    if (!sidebarOpen) return null;
    
    return (
      <div className="fixed inset-0 z-50">
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 z-50 h-full w-80 bg-gradient-to-b from-slate-900/95 via-slate-900/80 to-slate-950/95 backdrop-blur-2xl border-r border-slate-700/30 overflow-hidden">
          {/* Decorative gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-orange-500/5 via-transparent to-purple-500/5 pointer-events-none" />
          
          <div className="relative z-10 p-6 h-full flex flex-col">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-orange-400 via-orange-500 to-red-500 bg-clip-text text-transparent">
                  KireMisu
                </h1>
                <p className="text-slate-400 text-sm mt-1">Your manga universe</p>
              </div>
              <button 
                onClick={() => setSidebarOpen(false)} 
                className="p-2 rounded-xl bg-slate-800/30 border border-slate-700/30 text-slate-400 hover:text-white hover:bg-slate-700/40 transition-all"
              >
                <X size={20} />
              </button>
            </div>
            
            <nav className="space-y-2 flex-1">
              {navigationItems.map((item) => {
                const Icon = item.icon;
                const isActive = currentView === item.id;
                return (
                  <div key={item.id} className="relative group">
                    {isActive && (
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-orange-400 to-orange-600 rounded-r-full" />
                    )}
                    
                    <button
                      onClick={() => {
                        setCurrentView(item.id);
                        setSidebarOpen(false);
                      }}
                      className={`w-full flex items-center px-4 py-3 rounded-xl transition-all duration-300 ${
                        isActive 
                          ? 'bg-gradient-to-r from-orange-500/20 to-red-500/20 border border-orange-500/30' 
                          : 'hover:bg-slate-800/40 border border-transparent'
                      }`}
                    >
                      <div className={`p-2 rounded-lg mr-3 transition-all ${
                        isActive 
                          ? 'bg-gradient-to-r from-orange-500 to-red-500' 
                          : 'bg-slate-800/50'
                      }`}>
                        <Icon size={16} className={isActive ? 'text-white' : 'text-slate-400'} />
                      </div>
                      <span className={`font-medium ${
                        isActive ? 'text-white' : 'text-slate-300'
                      }`}>
                        {item.label}
                      </span>
                    </button>
                  </div>
                );
              })}
            </nav>

            {/* Mobile user profile */}
            <div className="mt-6">
              <div className="bg-gradient-to-r from-slate-800/50 to-slate-800/30 backdrop-blur-sm rounded-xl p-4 border border-slate-700/30">
                <div className="flex items-center">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-orange-500 to-red-500 flex items-center justify-center">
                    <span className="text-white font-bold">U</span>
                  </div>
                  <div className="ml-3">
                    <p className="text-white font-medium">Reader User</p>
                    <p className="text-slate-400 text-sm">🔥 12 day streak</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Desktop Sidebar
  const DesktopSidebar = () => (
    <div className="hidden md:flex w-80 bg-gradient-to-b from-slate-900/80 via-slate-900/60 to-slate-950/80 backdrop-blur-2xl border-r border-slate-700/30 flex-col h-screen relative overflow-hidden">
      {/* Decorative gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-orange-500/5 via-transparent to-purple-500/5 pointer-events-none" />
      
      <div className="relative z-10 p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-400 via-orange-500 to-red-500 bg-clip-text text-transparent">
            KireMisu
          </h1>
          <p className="text-slate-400 text-sm mt-2 font-medium">Your personal manga universe</p>
          
          {/* Stats mini cards */}
          <div className="grid grid-cols-2 gap-3 mt-6">
            <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl p-3 border border-slate-700/30">
              <p className="text-orange-400 text-xs font-medium">SERIES</p>
              <p className="text-white text-lg font-bold">156</p>
            </div>
            <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl p-3 border border-slate-700/30">
              <p className="text-blue-400 text-xs font-medium">READ</p>
              <p className="text-white text-lg font-bold">67%</p>
            </div>
          </div>
        </div>
        
        <nav className="space-y-3">
          {navigationItems.map((item, index) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <div key={item.id} className="relative group">
                {/* Active indicator line */}
                {isActive && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-orange-400 to-orange-600 rounded-r-full" />
                )}
                
                <button
                  onClick={() => setCurrentView(item.id)}
                  className={`w-full flex items-center px-4 py-4 rounded-2xl transition-all duration-300 group relative overflow-hidden ${
                    isActive 
                      ? 'bg-gradient-to-r from-orange-500/20 to-red-500/20 border border-orange-500/30 shadow-lg shadow-orange-500/10' 
                      : 'hover:bg-slate-800/40 hover:border-slate-700/50 border border-transparent'
                  }`}
                >
                  {/* Subtle glow effect for active item */}
                  {isActive && (
                    <div className="absolute inset-0 bg-gradient-to-r from-orange-500/10 to-red-500/10 rounded-2xl blur-sm" />
                  )}
                  
                  <div className={`relative z-10 flex items-center w-full ${
                    isActive ? 'text-white' : 'text-slate-300 group-hover:text-white'
                  }`}>
                    <div className={`p-2 rounded-xl mr-4 transition-all duration-300 ${
                      isActive 
                        ? 'bg-gradient-to-r from-orange-500 to-red-500 shadow-lg' 
                        : 'bg-slate-800/50 group-hover:bg-slate-700/50'
                    }`}>
                      <Icon size={18} className={isActive ? 'text-white' : 'text-slate-400 group-hover:text-white'} />
                    </div>
                    
                    <div className="flex-1 text-left">
                      <p className={`font-medium transition-colors ${
                        isActive ? 'text-white' : 'text-slate-300 group-hover:text-white'
                      }`}>
                        {item.label}
                      </p>
                      {item.id === 'library' && (
                        <p className="text-xs text-slate-500 mt-0.5">156 series</p>
                      )}
                      {item.id === 'downloads' && (
                        <p className="text-xs text-slate-500 mt-0.5">3 active</p>
                      )}
                      {item.id === 'lists' && (
                        <p className="text-xs text-slate-500 mt-0.5">12 collections</p>
                      )}
                    </div>
                    
                    {/* Notification badges */}
                    {item.id === 'downloads' && (
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                    )}
                    {item.id === 'library' && (
                      <div className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full font-medium">
                        3
                      </div>
                    )}
                  </div>
                </button>
              </div>
            );
          })}
        </nav>

        {/* Quick Actions Section */}
        <div className="mt-8 space-y-3">
          <p className="text-slate-400 text-xs font-medium uppercase tracking-wider">Quick Actions</p>
          
          <button className="w-full flex items-center p-3 rounded-xl bg-slate-800/30 border border-slate-700/30 hover:bg-slate-700/40 transition-all duration-300 group">
            <div className="p-2 rounded-lg bg-green-500/20 mr-3 group-hover:bg-green-500/30 transition-colors">
              <Plus size={16} className="text-green-400" />
            </div>
            <span className="text-slate-300 group-hover:text-white transition-colors font-medium">Add Series</span>
          </button>
          
          <button className="w-full flex items-center p-3 rounded-xl bg-slate-800/30 border border-slate-700/30 hover:bg-slate-700/40 transition-all duration-300 group">
            <div className="p-2 rounded-lg bg-blue-500/20 mr-3 group-hover:bg-blue-500/30 transition-colors">
              <Download size={16} className="text-blue-400" />
            </div>
            <span className="text-slate-300 group-hover:text-white transition-colors font-medium">Sync MangaDex</span>
          </button>
        </div>
      </div>

      {/* User Profile Section */}
      <div className="relative z-10 p-6 mt-auto">
        <div className="bg-gradient-to-r from-slate-800/50 to-slate-800/30 backdrop-blur-sm rounded-2xl p-4 border border-slate-700/30 hover:border-orange-500/30 transition-all duration-300 cursor-pointer group">
          <div className="flex items-center">
            <div className="relative">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-orange-500 to-red-500 flex items-center justify-center shadow-lg">
                <span className="text-white font-bold text-lg">U</span>
              </div>
              {/* Online indicator */}
              <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-slate-900" />
            </div>
            
            <div className="ml-4 flex-1">
              <p className="text-white font-semibold">Reader User</p>
              <p className="text-slate-400 text-sm">Manga Enthusiast</p>
            </div>
            
            <button className="text-slate-400 hover:text-white transition-colors opacity-0 group-hover:opacity-100">
              <Settings size={16} />
            </button>
          </div>
          
          {/* Reading streak */}
          <div className="mt-3 pt-3 border-t border-slate-700/30">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Reading Streak</span>
              <span className="text-orange-400 font-medium">🔥 12 days</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // Header
  const Header = () => (
    <header className="bg-slate-900/60 backdrop-blur-xl border-b border-slate-800/50 p-4">
      <div className="flex items-center">
        <button
          className="md:hidden mr-4 text-slate-300 hover:text-orange-400 p-2"
          onClick={() => setSidebarOpen(true)}
        >
          <Menu size={20} />
        </button>
        
        <div className="flex-1 max-w-md">
          <Input
            placeholder="Search manga, authors, genres..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            icon={<Search size={18} />}
          />
        </div>
        
        <div className="ml-4 flex items-center space-x-3">
          <Button variant="glass" size="sm">
            <Plus size={16} className="mr-2" />
            Add Series
          </Button>
        </div>
      </div>
    </header>
  );

  // Dashboard View
  const DashboardView = () => (
    <div className="p-6 space-y-8 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 min-h-screen">
      {/* Welcome Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Welcome back!</h1>
          <p className="text-slate-400 mt-1">Ready to continue your manga journey?</p>
        </div>
        <div className="hidden md:flex items-center space-x-4">
          <Button variant="outline">
            <TrendingUp size={16} className="mr-2" />
            Trending
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard 
          title="Total Series" 
          value="156" 
          change="+12"
          icon={<Library size={20} />}
          color="text-blue-400"
        />
        <StatsCard 
          title="Chapters Read" 
          value="2,847" 
          change="+89"
          icon={<BookOpen size={20} />}
          color="text-green-400"
        />
        <StatsCard 
          title="Reading Progress" 
          value="67%" 
          change="+5%"
          icon={<TrendingUp size={20} />}
          color="text-orange-400"
        />
        <StatsCard 
          title="Lists Created" 
          value="12" 
          change="+2"
          icon={<Heart size={20} />}
          color="text-purple-400"
        />
      </div>

      {/* Continue Reading Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Continue Reading</h2>
          <Button variant="ghost" size="sm">View All</Button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {mockSeries.filter(s => s.readChapters > 0).map(series => (
            <Card key={series.id} className="p-0 overflow-hidden group" onClick={() => setSelectedSeries(series)}>
              <div className="relative">
                <img 
                  src={series.cover} 
                  alt={series.title}
                  className="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-500"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                <div className="absolute bottom-4 left-4 right-4">
                  <h3 className="text-white font-bold text-lg mb-1">{series.title}</h3>
                  <p className="text-slate-300 text-sm">{series.author}</p>
                  <div className="flex items-center justify-between mt-3">
                    <span className="text-orange-400 text-sm font-medium">
                      Chapter {series.readChapters}/{series.chapters}
                    </span>
                    {series.newChapters && (
                      <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                        {series.newChapters} new
                      </span>
                    )}
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2 mt-2">
                    <div 
                      className="bg-gradient-to-r from-orange-500 to-orange-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${(series.readChapters / series.chapters) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6 bg-gradient-to-br from-blue-500/20 to-purple-500/20 border-blue-500/30">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-white">Discover New Manga</h3>
              <p className="text-slate-300 mt-1">Browse trending and popular series</p>
            </div>
            <Button variant="glass">
              Explore
            </Button>
          </div>
        </Card>
        
        <Card className="p-6 bg-gradient-to-br from-green-500/20 to-emerald-500/20 border-green-500/30">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-white">Sync with MangaDex</h3>
              <p className="text-slate-300 mt-1">Keep your progress in sync</p>
            </div>
            <Button variant="glass">
              Sync Now
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );

  // Library View
  const LibraryView = () => (
    <div className="p-6 space-y-6 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 min-h-screen">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">Your Library</h2>
        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
            <Filter size={16} className="mr-2" />
            Filters
          </Button>
          
          <div className="flex bg-slate-800/50 rounded-xl p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-orange-500 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              <Grid size={16} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-orange-500 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              <List size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <Card className="p-6" gradient>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-white mb-2">Status</label>
              <select className="w-full p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-white">
                <option>All Status</option>
                <option>Ongoing</option>
                <option>Completed</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-white mb-2">Genre</label>
              <select className="w-full p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-white">
                <option>All Genres</option>
                <option>Action</option>
                <option>Romance</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-white mb-2">Tags</label>
              <select className="w-full p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-white">
                <option>All Tags</option>
                <option>Must Read</option>
                <option>Currently Reading</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-white mb-2">Sort By</label>
              <select className="w-full p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-white">
                <option>Recently Added</option>
                <option>Title A-Z</option>
                <option>Rating</option>
              </select>
            </div>
          </div>
        </Card>
      )}

      {/* Series Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
        {mockSeries.map(series => (
          <Card key={series.id} className="p-0 overflow-hidden group" onClick={() => setSelectedSeries(series)}>
            <div className="relative">
              <img
                src={series.cover}
                alt={series.title}
                className="w-full h-64 object-cover group-hover:scale-110 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              
              {/* Status badges */}
              <div className="absolute top-3 right-3 flex flex-col gap-2">
                {series.trending && (
                  <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full flex items-center">
                    🔥 Trending
                  </span>
                )}
                {series.isNew && (
                  <span className="bg-green-500 text-white text-xs px-2 py-1 rounded-full">
                    New
                  </span>
                )}
                {series.newChapters && (
                  <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded-full">
                    +{series.newChapters}
                  </span>
                )}
              </div>

              {/* Progress bar */}
              <div className="absolute bottom-0 left-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <div className="w-full bg-slate-700 rounded-full h-1.5">
                  <div 
                    className="bg-gradient-to-r from-orange-500 to-orange-600 h-1.5 rounded-full"
                    style={{ width: `${(series.readChapters / series.chapters) * 100}%` }}
                  />
                </div>
              </div>
            </div>
            
            <div className="p-4">
              <h3 className="font-semibold text-white text-sm line-clamp-2 mb-1 group-hover:text-orange-400 transition-colors">
                {series.title}
              </h3>
              <p className="text-slate-400 text-xs mb-2">{series.author}</p>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <Star size={12} className="text-orange-400 fill-current" />
                  <span className="text-xs text-slate-400">{series.rating}</span>
                </div>
                <span className="text-xs text-slate-500">
                  {series.readChapters}/{series.chapters}
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );

  // Series Detail View (simplified for space)
  const SeriesDetailView = ({ series }) => (
    <div className="p-6 space-y-6 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 min-h-screen">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" onClick={() => setSelectedSeries(null)}>
          <ChevronLeft size={20} />
        </Button>
        <h2 className="text-2xl font-bold text-white">{series.title}</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <Card className="p-6" gradient>
            <img src={series.cover} alt={series.title} className="w-full rounded-xl mb-4" />
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-white mb-1">Author</h3>
                <p className="text-slate-400">{series.author}</p>
              </div>
              <div>
                <h3 className="font-semibold text-white mb-1">Status</h3>
                <span className={`px-3 py-1 rounded-full text-sm ${series.status === 'Ongoing' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'}`}>
                  {series.status}
                </span>
              </div>
              <div>
                <h3 className="font-semibold text-white mb-2">Genres</h3>
                <div className="flex flex-wrap gap-2">
                  {series.genres.map(genre => (
                    <span key={genre} className="bg-slate-700/50 text-slate-300 text-sm px-3 py-1 rounded-full">
                      {genre}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <Button className="flex-1">Continue Reading</Button>
                <Button variant="outline">
                  <Bookmark size={16} />
                </Button>
              </div>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card className="p-6" gradient>
            <h3 className="text-xl font-bold text-white mb-6">Chapters</h3>
            <div className="space-y-3">
              {mockChapters.map(chapter => (
                <div
                  key={chapter.id}
                  className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl hover:bg-slate-700/50 cursor-pointer transition-all"
                  onClick={() => setSelectedChapter(chapter)}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${chapter.read ? 'bg-orange-500' : 'bg-slate-600'}`} />
                    <div>
                      <h4 className="font-medium text-white">Chapter {chapter.number}</h4>
                      <p className="text-sm text-slate-400">{chapter.title}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {chapter.downloaded && <Download size={16} className="text-green-400" />}
                    <button className="text-slate-400 hover:text-white">
                      <MoreHorizontal size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );

  // Lists View
  const ListsView = () => (
    <div className="p-6 space-y-6 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 min-h-screen">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">Reading Lists</h2>
        <Button>
          <Plus size={16} className="mr-2" />
          New List
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {mockLists.map(list => (
          <Card key={list.id} className="p-6 group" onClick={() => {}}>
            <div className="flex items-center justify-between mb-4">
              <div className={`w-12 h-12 rounded-2xl ${list.color} flex items-center justify-center text-2xl`}>
                {list.emoji}
              </div>
              <button className="text-slate-400 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <MoreHorizontal size={16} />
              </button>
            </div>
            <h3 className="font-bold text-white text-lg mb-1">{list.name}</h3>
            <p className="text-slate-400">{list.count} series</p>
            <div className="mt-4 flex items-center text-sm text-slate-500">
              <Clock size={14} className="mr-1" />
              Last updated today
            </div>
          </Card>
        ))}
      </div>
    </div>
  );

  // Other simplified views
  const DownloadsView = () => (
    <div className="p-6 space-y-6 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 min-h-screen">
      <h2 className="text-2xl font-bold text-white">Downloads</h2>
      <Card className="p-8 text-center" gradient>
        <Download size={48} className="text-slate-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-white mb-2">No Active Downloads</h3>
        <p className="text-slate-400">Download queue and history will appear here</p>
      </Card>
    </div>
  );

  const SettingsView = () => (
    <div className="p-6 space-y-6 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 min-h-screen">
      <h2 className="text-2xl font-bold text-white">Settings</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6" gradient>
          <h3 className="text-lg font-bold text-white mb-4">Library Settings</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-white mb-2">Library Path</label>
              <Input value="/manga/library" />
            </div>
            <Button>Update Path</Button>
          </div>
        </Card>

        <Card className="p-6" gradient>
          <h3 className="text-lg font-bold text-white mb-4">MangaDex Integration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-white mb-2">API Token</label>
              <Input placeholder="Enter your MangaDex API token" />
            </div>
            <Button>Test Connection</Button>
          </div>
        </Card>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <DesktopSidebar />
      <MobileNav />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        
        <main className="flex-1 overflow-auto">
          {selectedChapter ? (
            <div>Chapter Reader (simplified for demo)</div>
          ) : selectedSeries ? (
            <SeriesDetailView series={selectedSeries} />
          ) : (
            <>
              {currentView === 'dashboard' && <DashboardView />}
              {currentView === 'library' && <LibraryView />}
              {currentView === 'lists' && <ListsView />}
              {currentView === 'downloads' && <DownloadsView />}
              {currentView === 'settings' && <SettingsView />}
            </>
          )}
        </main>
      </div>
    </div>
  );
};

export default KireMisuApp;