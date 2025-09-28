import { useBranch } from '@/contexts/BranchContext';
import { useRepository } from '@/contexts/RepositoryContext';
import { useAuth } from '@/contexts/AuthContext';
import GitHubAPI from '@/lib/github-api';
import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Code, Github, Star, GitBranch, Calendar, User, Lock, Globe, ExternalLink, Heart, GitFork, Globe2, Users, Zap, Clock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

// Custom CSS for animations
const customStyles = `
  @keyframes slide-up {
    from { 
      opacity: 0; 
      transform: translateY(30px); 
    }
    to { 
      opacity: 1; 
      transform: translateY(0); 
    }
  }
  
  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes scale-in {
    from { 
      opacity: 0; 
      transform: scale(0.8); 
    }
    to { 
      opacity: 1; 
      transform: scale(1); 
    }
  }
  
  @keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
  }
  
  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 5px hsl(var(--primary) / 0.3); }
    50% { box-shadow: 0 0 20px hsl(var(--primary) / 0.6); }
  }
  
  .animate-slide-up {
    animation: slide-up 0.6s ease-out forwards;
  }
  
  .animate-fade-in {
    animation: fade-in 0.8s ease-out forwards;
  }
  
  .animate-scale-in {
    animation: scale-in 0.5s ease-out forwards;
  }
  
  .animate-float {
    animation: float 3s ease-in-out infinite;
  }
  
  .animate-pulse-glow {
    animation: pulse-glow 2s ease-in-out infinite;
  }
  
  .language-bar {
    position: relative;
    overflow: hidden;
  }
  
  .language-bar::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background: linear-gradient(90deg, transparent, hsl(var(--foreground) / 0.3), transparent);
    width: 100%;
    transform: translateX(-100%);
    animation: shimmer 2s infinite;
  }
  
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
`;

// Repository View Component
const RepositoryView = ({ repository }: { repository: any }) => {
  const { token } = useAuth();
  const [contributors, setContributors] = useState<any[]>([]);
  const [languages, setLanguages] = useState<{ [key: string]: number }>({});
  const [stargazers, setStargazers] = useState<any[]>([]);
  const [forks, setForks] = useState<any[]>([]);
  const [watchers, setWatchers] = useState<any[]>([]);
  const [releases, setReleases] = useState<any[]>([]);
  const [packages, setPackages] = useState<any[]>([]);
  const [deployments, setDeployments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !repository?.owner?.login || !repository?.name) return;
    const githubAPI = new GitHubAPI(token);
    setLoading(true);
    
    // Check if we're currently rate limited
    if (githubAPI.isCurrentlyRateLimited()) {
      const timeUntilReset = githubAPI.getTimeUntilReset();
      const resetTime = new Date(Date.now() + timeUntilReset);
      toast.error('GitHub API rate limit exceeded', {
        description: `Service will be available again at ${resetTime.toLocaleTimeString()}`,
        duration: 10000,
      });
      setLoading(false);
      return;
    }
    
    // Fetch repository data with proper error handling
    const fetchRepositoryData = async () => {
      try {
        setError(null); // Clear any previous errors
        
        // Fetch contributors and languages with rate limit protection
        const [contributors, languages] = await Promise.allSettled([
          githubAPI.getRepositoryContributors(repository.owner.login, repository.name),
          githubAPI.getRepositoryLanguages(repository.owner.login, repository.name),
        ]);

        // Handle contributors result
        if (contributors.status === 'fulfilled') {
          setContributors(contributors.value || []);
        } else {
          console.warn('Failed to fetch contributors:', contributors.reason);
          setContributors([]);
        }

        // Handle languages result
        if (languages.status === 'fulfilled') {
          setLanguages(languages.value || {});
        } else {
          console.warn('Failed to fetch languages:', languages.reason);
          setLanguages({});
        }

        // Set empty arrays for other data (not implemented in API yet)
        setStargazers([]);
        setForks([]);
        setWatchers([]);
        setReleases([]);
        setPackages([]);
        setDeployments([]);

      } catch (error: any) {
        console.error('Error fetching repository data:', error);
        
        // Handle rate limit errors specifically
        if (error?.message?.includes('rate limit') || error?.message?.includes('Rate limit exceeded')) {
          const errorMsg = 'GitHub API rate limit exceeded. Please wait before making more requests.';
          setError(errorMsg);
          toast.error('Rate limit exceeded', {
            description: 'The limit resets every hour. You can still view basic repository information.',
            duration: 10000,
          });
          return;
        }

        // Handle authentication errors
        if (error?.message?.includes('401') || error?.message?.includes('Unauthorized')) {
          const errorMsg = 'Authentication required to view detailed repository information.';
          setError(errorMsg);
          toast.error('Authentication required', {
            description: 'Please log in to view repository details.',
            duration: 5000,
          });
          return;
        }

        // Handle network errors
        if (error?.message?.includes('fetch') || error?.message?.includes('Network')) {
          const errorMsg = 'Network error occurred while loading repository data.';
          setError(errorMsg);
          toast.error('Network error', {
            description: 'Please check your connection and try again.',
            duration: 5000,
          });
          return;
        }

        // Handle other errors gracefully
        const errorMsg = 'Some repository information may not be available.';
        setError(errorMsg);
        toast.error('Failed to load repository data', {
          description: 'Basic repository information is still available.',
          duration: 5000,
        });
        
        // Set empty data to prevent crashes
        setContributors([]);
        setLanguages({});
        setStargazers([]);
        setForks([]);
        setWatchers([]);
        setReleases([]);
        setPackages([]);
        setDeployments([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRepositoryData();
  }, [token, repository]);

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    if (diffInSeconds < 31536000) return `${Math.floor(diffInSeconds / 2592000)}mo ago`;
    return `${Math.floor(diffInSeconds / 31536000)}y ago`;
  };

  const getLanguageColor = (language: string) => {
    const colors: { [key: string]: string } = {
      'JavaScript': '#f1e05a',
      'TypeScript': '#2b7489',
      'Python': '#3572A5',
      'Java': '#b07219',
      'C++': '#f34b7d',
      'C#': '#178600',
      'Go': '#00ADD8',
      'Rust': '#dea584',
      'PHP': '#4F5D95',
      'Ruby': '#701516',
      'Swift': '#ffac45',
      'Kotlin': '#F18E33',
      'Scala': '#c22d40',
      'R': '#198ce7',
      'Dart': '#00B4AB',
      'Elixir': '#6e4a7e',
      'Clojure': '#db5855',
      'Haskell': '#5e5086',
      'OCaml': '#3be133',
      'F#': '#b845fc',
      'Crystal': '#000100',
      'Nim': '#37775b',
      'Zig': '#ec915c',
      'V': '#4f87c4',
      'Lua': '#000080',
      'Perl': '#0298c3',
      'Shell': '#89e051',
      'PowerShell': '#012456',
      'Batchfile': '#C1F12E',
      'Makefile': '#427819',
      'Dockerfile': '#384d54',
      'HTML': '#e34c26',
      'CSS': '#563d7c',
      'SCSS': '#c6538c',
      'Sass': '#a53b70',
      'Less': '#1d365d',
      'Vue': '#2c3e50',
      'React': '#61dafb',
      'Angular': '#dd0031',
      'Svelte': '#ff3e00',
      'Solidity': '#363636',
      'Assembly': '#6E4C13',
      'C': '#555555',
      'Objective-C': '#438eff',
      'Objective-C++': '#6866fb',
      'CoffeeScript': '#244776',
      'TeX': '#3D6117',
      'Markdown': '#083fa1',
      'YAML': '#cb171e',
      'JSON': '#292b36',
      'XML': '#f0db4f',
      'SVG': '#ff9900',
      'GraphQL': '#e10098',
      'Protocol Buffer': '#e10098',
      'Thrift': '#e10098',
      'WebAssembly': '#654ff0',
      'WebVTT': '#e10098',
      'WebIDL': '#e10098',
      'WebGL': '#e10098',
      'WebGPU': '#e10098',
      'WebRTC': '#e10098',
      'WebSocket': '#e10098',
      'WebWorker': '#e10098',
      'WebStorage': '#e10098',
      'WebCrypto': '#e10098',
      'WebAuthn': '#e10098',
      'WebPush': '#e10098',
      'WebShare': '#e10098',
      'WebBluetooth': '#e10098',
      'WebUSB': '#e10098',
      'WebSerial': '#e10098',
      'WebHID': '#e10098',
      'WebNFC': '#e10098',
      'WebXR': '#e10098',
      'WebCodecs': '#e10098',
      'WebTransport': '#e10098',
      'WebNN': '#e10098',
    };
    return colors[language] || '#6e7681';
  };

  const totalBytes = Object.values(languages).reduce((sum: number, bytes: number) => sum + bytes, 0);

  // Show loading state
  if (loading) {
    return (
      <>
        <style dangerouslySetInnerHTML={{ __html: customStyles }} />
        <div className="max-w-6xl mx-auto space-y-12 bg-black-900 p-8">
          <div className="text-center space-y-8">
            <div className="flex flex-col items-center space-y-6">
              <div className="w-24 h-24 rounded-full bg-gray-300 animate-pulse"></div>
              <div className="space-y-4">
                <div className="h-12 bg-gray-300 rounded animate-pulse w-96"></div>
                <div className="h-6 bg-gray-300 rounded animate-pulse w-64 mx-auto"></div>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="text-center p-6 bg-black-800 rounded-2xl animate-pulse">
                <div className="h-8 bg-gray-300 rounded mb-2"></div>
                <div className="h-4 bg-gray-300 rounded"></div>
              </div>
            ))}
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: customStyles }} />
      <div className="max-w-6xl mx-auto space-y-12 bg-black-900 p-8">
        {/* Error Banner */}
        {error && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-800">{error}</p>
              </div>
            </div>
          </div>
        )}
        {/* Hero Section with Owner Profile */}
        <div className="text-center space-y-8">
          <div className="flex flex-col items-center space-y-6">
            {/* Owner Profile */}
            <div className="relative group">
              <div className="w-24 h-24 rounded-full overflow-hidden border-4 border-white shadow-2xl animate-scale-in">
                <img
                  src={repository.owner?.avatar_url || 'https://github.com/github.png'}
                  alt={repository.owner?.login}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-orange-500 rounded-full border-3 border-white animate-pulse-glow"></div>
            </div>
            
            {/* Repository Info */}
            <div className="space-y-4">
              <h1 className="text-5xl md:text-6xl font-bold text-white animate-slide-up">
                {repository.name}
              </h1>
              <p className="text-xl text-black-300 max-w-3xl mx-auto leading-relaxed animate-slide-up" style={{ animationDelay: '0.2s' }}>
                {repository.description || "No description available"}
              </p>
              
              {/* Owner Info */}
              <div className="flex items-center justify-center gap-2 text-black-400 animate-slide-up" style={{ animationDelay: '0.4s' }}>
                <span>by</span>
                <a 
                  href={`https://github.com/${repository.owner?.login}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-orange-400 hover:text-orange-300 transition-colors"
                >
                  {repository.owner?.login}
                </a>
              </div>
            </div>
          </div>

          {/* Website Link */}
          {repository.homepage && (
            <div className="animate-slide-up" style={{ animationDelay: '0.6s' }}>
              <a
                href={repository.homepage}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 bg-orange-500 text-white rounded-full hover:bg-orange-600 transition-all duration-300 font-medium"
              >
                <Globe2 className="w-4 h-4" />
                Visit Website
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          )}

          {/* Topics */}
          {repository.topics && repository.topics.length > 0 && (
            <div className="flex flex-wrap justify-center gap-2 animate-slide-up" style={{ animationDelay: '0.8s' }}>
              {repository.topics.map((topic: string) => (
                <span
                  key={topic}
                  className="px-3 py-1 bg-black-800 text-black-300 rounded-full text-sm font-medium hover:bg-black-700 transition-all duration-300 cursor-pointer"
                >
                  #{topic}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center p-6 bg-black-800 rounded-2xl shadow-sm border border-black-700 hover:shadow-md transition-all duration-300 animate-scale-in" style={{ animationDelay: '0.1s' }}>
            <div className="text-3xl font-bold text-white mb-2">{repository.stargazers_count}</div>
            <div className="text-sm text-black-400 font-medium">Stars</div>
          </div>
          <div className="text-center p-6 bg-black-800 rounded-2xl shadow-sm border border-black-700 hover:shadow-md transition-all duration-300 animate-scale-in" style={{ animationDelay: '0.2s' }}>
            <div className="text-3xl font-bold text-white mb-2">{repository.forks_count}</div>
            <div className="text-sm text-black-400 font-medium">Forks</div>
          </div>
          <div className="text-center p-6 bg-black-800 rounded-2xl shadow-sm border border-black-700 hover:shadow-md transition-all duration-300 animate-scale-in" style={{ animationDelay: '0.3s' }}>
            <div className="text-3xl font-bold text-white mb-2">{repository.language || "N/A"}</div>
            <div className="text-sm text-black-400 font-medium">Language</div>
          </div>
          <div className="text-center p-6 bg-black-800 rounded-2xl shadow-sm border border-black-700 hover:shadow-md transition-all duration-300 animate-scale-in" style={{ animationDelay: '0.4s' }}>
            <div className="text-3xl font-bold text-white mb-2">{repository.default_branch}</div>
            <div className="text-sm text-black-400 font-medium">Branch</div>
          </div>
        </div>

        {/* Languages with Modern Animation */}
        {Object.keys(languages).length > 0 && (
          <Card className="bg-black-800 border border-black-700 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-xl text-white">
                <Code className="w-5 h-5 text-orange-500" />
                Languages
              </CardTitle>
              <CardDescription className="text-black-400">
                Programming languages used in this repository
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {Object.entries(languages).map(([lang, bytes], index) => {
                  const percentage = ((bytes / totalBytes) * 100).toFixed(1);
                  return (
                    <div key={lang} className="space-y-3 animate-slide-up" style={{ animationDelay: `${index * 0.1}s` }}>
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: getLanguageColor(lang) }}
                          ></div>
                          <span className="font-semibold text-white">{lang}</span>
                        </div>
                        <span className="text-sm text-black-400">{percentage}%</span>
                      </div>
                      <div className="w-full bg-black-700 rounded-full h-2 overflow-hidden">
                        <div
                          className="language-bar h-full rounded-full transition-all duration-1000 ease-out"
                          style={{
                            width: `${percentage}%`,
                            backgroundColor: getLanguageColor(lang),
                          }}
                        ></div>
                      </div>
                      <div className="text-xs text-black-500 text-right">
                        {bytes.toLocaleString()} bytes
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Contributors */}
        {contributors.length > 0 && (
          <Card className="bg-black-800 border border-black-700 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-xl text-white">
                <Users className="w-5 h-5 text-orange-500" />
                Contributors
              </CardTitle>
              <CardDescription className="text-black-400">
                People who have contributed to this repository
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {contributors.slice(0, 12).map((contributor: any, index: number) => (
                  <a
                    key={contributor.id}
                    href={`/hub/profile/${contributor.login}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex flex-col items-center p-4 rounded-xl bg-black-700 hover:bg-black transition-all duration-300 transform hover:scale-105"
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    <div className="relative mb-3">
                      <img
                        src={contributor.avatar_url}
                        alt={contributor.login}
                        className="w-16 h-16 rounded-full border-3 border-white shadow-lg group-hover:shadow-xl transition-all duration-300"
                      />
                      <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-orange-500 rounded-full border-2 border-white animate-pulse"></div>
                    </div>
                    <span className="text-sm font-medium text-center text-white group-hover:text-orange-400 transition-colors duration-300">
                      {contributor.login}
                    </span>
                    <span className="text-xs text-black-400">
                      {contributor.contributions} contributions
                    </span>
                  </a>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stargazers with Profile Photos */}
        <Card className="bg-black-800 border border-black-700 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-3 text-xl text-white">
              <Star className="w-5 h-5 text-orange-500" />
              Stargazers
            </CardTitle>
            <CardDescription className="text-black-400">
              People who have starred this repository
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {Array.from({ length: Math.min(repository.stargazers_count, 30) }, (_, i) => (
                <div
                  key={i}
                  className="relative group animate-float"
                  style={{ animationDelay: `${i * 0.1}s` }}
                >
                  <div className="w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center text-white shadow-lg group-hover:shadow-xl transition-all duration-300 transform group-hover:scale-110">
                    <Star className="w-6 h-6" />
                  </div>
                  <div className="absolute -top-1 -right-1 w-4 h-4 bg-white rounded-full border-2 border-black-800 animate-pulse"></div>
                </div>
              ))}
              {repository.stargazers_count > 30 && (
                <div className="w-12 h-12 bg-black-700 rounded-full flex items-center justify-center text-xs font-bold text-black-400 border-2 border-dashed border-black-600">
                  +{repository.stargazers_count - 30}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Forks with Profile Photos */}
        <Card className="bg-black-800 border border-black-700 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-3 text-xl text-white">
              <GitFork className="w-5 h-5 text-orange-500" />
              Forks
            </CardTitle>
            <CardDescription className="text-black-400">
              People who have forked this repository
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {Array.from({ length: Math.min(repository.forks_count, 20) }, (_, i) => (
                <div
                  key={i}
                  className="relative group animate-float"
                  style={{ animationDelay: `${i * 0.15}s` }}
                >
                  <div className="w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center text-white shadow-lg group-hover:shadow-xl transition-all duration-300 transform group-hover:scale-110">
                    <GitFork className="w-6 h-6" />
                  </div>
                  <div className="absolute -top-1 -right-1 w-4 h-4 bg-white rounded-full border-2 border-black-800 animate-pulse"></div>
                </div>
              ))}
              {repository.forks_count > 20 && (
                <div className="w-12 h-12 bg-black-700 rounded-full flex items-center justify-center text-xs font-bold text-black-400 border-2 border-dashed border-black-600">
                  +{repository.forks_count - 20}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Repository Details */}
        <Card className="bg-black-800 border border-black-700 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-3 text-xl text-white">
              <Github className="w-5 h-5 text-black-400" />
              Repository Details
            </CardTitle>
            <CardDescription className="text-black-400">
              Detailed information about this repository
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-4 rounded-lg bg-black-700">
                  <User className="w-5 h-5 text-orange-500" />
                  <div>
                    <span className="text-sm text-black-400">Owner:</span>
                    <span className="ml-2 font-medium text-white">{repository.owner?.login}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg bg-black-700">
                  <Calendar className="w-5 h-5 text-orange-500" />
                  <div>
                    <span className="text-sm text-black-400">Created:</span>
                    <span className="ml-2 font-medium text-white">{new Date(repository.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg bg-black-700">
                  <Clock className="w-5 h-5 text-orange-500" />
                  <div>
                    <span className="text-sm text-black-400">Last Updated:</span>
                    <span className="ml-2 font-medium text-white">{getRelativeTime(repository.updated_at)}</span>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-4 rounded-lg bg-black-700">
                  {repository.private ? (
                    <Lock className="w-5 h-5 text-red-400" />
                  ) : (
                    <Globe className="w-5 h-5 text-green-400" />
                  )}
                  <div>
                    <span className="text-sm text-black-400">Visibility:</span>
                    <Badge variant={repository.private ? "destructive" : "default"} className="ml-2">
                      {repository.private ? "Private" : "Public"}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg bg-black-700">
                  <GitBranch className="w-5 h-5 text-orange-500" />
                  <div>
                    <span className="text-sm text-black-400">Type:</span>
                    <Badge variant="secondary" className="ml-2 capitalize">
                      {repository.type}
                    </Badge>
                  </div>
                </div>
                {repository.fork && (
                  <div className="flex items-center gap-3 p-4 rounded-lg bg-black-700">
                    <GitFork className="w-5 h-5 text-orange-500" />
                    <div>
                      <span className="text-sm text-black-400">Forked from:</span>
                      <span className="ml-2 font-medium text-white">Original Repository</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Sponsor Button */}
        <div className="text-center">
          <Button className="bg-orange-500 hover:bg-orange-600 text-white px-8 py-4 rounded-full text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
            <Heart className="w-5 h-5 mr-2" />
            Sponsor this project
          </Button>
        </div>
      </div>
    </>
  );
};

// Generic Branch View Component
const GenericBranchView = ({ selectedBranch, branchInfo }: { selectedBranch: string; branchInfo: any }) => {
  const { repository } = useRepository();
  const projectName = repository?.name || 'Project';

  if (!selectedBranch) {
    return (
      <div className="text-center">
        <h1 className="text-4xl font-bold">No branch selected</h1>
        <p className="text-lg text-slate-600 dark:text-slate-300">Please select a branch to see its details.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className={`p-3 rounded-full bg-primary`}>
            <div className="text-white">
              <GitBranch className="w-8 h-8" />
            </div>
          </div>
        </div>
        <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 via-cyan-600 to-blue-800 bg-clip-text text-transparent mb-4">
          {projectName} - {branchInfo.name}
        </h1>
        <p className="text-xl text-slate-600 dark:text-slate-300 max-w-3xl mx-auto">
          {branchInfo.description || `This is the ${branchInfo.name} branch.`}
        </p>
      </div>

      <Card className="glass-panel">
        <CardHeader>
          <CardTitle className={branchInfo.color}>Branch: {branchInfo.name}</CardTitle>
          <CardDescription>
            Last commit SHA: {branchInfo.sha}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <a href={branchInfo.githubUrl} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
              View on GitHub
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Main BranchWhat Component
export const BranchWhat = () => {
  const { selectedBranch, getBranchInfo } = useBranch();
  const { repository, isRepositoryLoaded } = useRepository();
  const branchInfo = getBranchInfo();

  // Always show repository info if we have repository data
  if (repository) {
    return <RepositoryView repository={repository} />;
  }

  // Otherwise show the generic branch content
  return <GenericBranchView selectedBranch={selectedBranch} branchInfo={branchInfo} />;
};