import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GitFork, Star, Clock, ExternalLink } from "lucide-react";
import { useRouter } from "next/navigation";
import { Repository } from "@/lib/github-api";

interface EnhancedRepositoryCardProps {
  repo: Repository;
}

export function EnhancedRepositoryCard({ repo }: EnhancedRepositoryCardProps) {
  const router = useRouter();

  const handleOpenInBeetle = () => {
    const repoData = JSON.stringify(repo);
    const encodedRepo = encodeURIComponent(repoData);
    router.push(`/contribution?repo=${encodedRepo}`);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffInDays === 0) {
      return 'Today';
    } else if (diffInDays === 1) {
      return 'Yesterday';
    } else if (diffInDays < 30) {
      return `${diffInDays} days ago`;
    } else if (diffInDays < 365) {
      const months = Math.floor(diffInDays / 30);
      return `${months} month${months > 1 ? 's' : ''} ago`;
    } else {
      const years = Math.floor(diffInDays / 365);
      return `${years} year${years > 1 ? 's' : ''} ago`;
    }
  };

  const getLanguageColor = (language: string) => {
    const colors: { [key: string]: string } = {
      'JavaScript': 'bg-yellow-500',
      'TypeScript': 'bg-blue-500',
      'Python': 'bg-green-500',
      'Java': 'bg-orange-500',
      'C++': 'bg-blue-600',
      'C': 'bg-gray-600',
      'C#': 'bg-purple-500',
      'PHP': 'bg-indigo-500',
      'Ruby': 'bg-red-500',
      'Go': 'bg-cyan-500',
      'Rust': 'bg-orange-600',
      'Swift': 'bg-orange-400',
      'Kotlin': 'bg-purple-600',
      'HTML': 'bg-orange-400',
      'CSS': 'bg-blue-400',
      'Shell': 'bg-gray-500',
    };
    return colors[language] || 'bg-gray-400';
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg font-bold truncate">{repo.name}</CardTitle>
            {repo.private && (
              <Badge variant="outline" className="text-xs mt-1">Private</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="flex-grow pb-3">
        <CardDescription className="text-sm mb-3 line-clamp-2">
          {repo.description || 'No description available'}
        </CardDescription>
        
        <div className="flex items-center space-x-4 text-sm text-muted-foreground mb-3">
          <div className="flex items-center space-x-1">
            <Star className="h-3 w-3" />
            <span>{repo.stargazers_count}</span>
          </div>
          <div className="flex items-center space-x-1">
            <GitFork className="h-3 w-3" />
            <span>{repo.forks_count}</span>
          </div>
        </div>
        
        <div className="flex items-center justify-between text-xs">
          {repo.language && (
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${getLanguageColor(repo.language)}`} />
              <span className="text-muted-foreground">{repo.language}</span>
            </div>
          )}
          <div className="flex items-center space-x-1 text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>{formatDate(repo.updated_at)}</span>
          </div>
        </div>
      </CardContent>
      
      <CardFooter className="flex justify-between items-center space-x-2 pt-3">
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => window.open(repo.html_url, '_blank')}
          className="flex items-center space-x-1"
        >
          <ExternalLink className="h-3 w-3" />
          <span>GitHub</span>
        </Button>
        <Button 
          size="sm" 
          onClick={handleOpenInBeetle}
        >
          Open in Beetle
        </Button>
      </CardFooter>
    </Card>
  );
}
