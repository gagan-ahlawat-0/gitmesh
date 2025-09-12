import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Repository } from '@/lib/github-api';
import { Star, GitFork, ExternalLink } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface ProjectCardProps {
  repo: Repository;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({ repo }) => {
  const router = useRouter();

  const handleOpenInBeetle = () => {
    const repoData = JSON.stringify(repo);
    const encodedRepo = encodeURIComponent(repoData);
    router.push(`/contribution?repo=${encodedRepo}`);
  };

  return (
    <Card className="bg-black shadow-lg rounded-lg flex flex-col h-full hover:shadow-orange-500/20 transition-shadow duration-300">
      <CardHeader>
        <CardTitle className="text-xl font-bold text-orange-500">{repo.name}</CardTitle>
      </CardHeader>
      <CardContent className="flex-grow">
        <p className="text-sm text-gray-400">{repo.description}</p>
      </CardContent>
      <CardFooter className="flex justify-between items-center mt-auto pt-4 border-t border-gray-800">
        <div className="flex items-center space-x-4 text-gray-400">
          <div className="flex items-center">
            <Star className="h-4 w-4 mr-1" />
            <span>{repo.stargazers_count}</span>
          </div>
          <div className="flex items-center">
            <GitFork className="h-4 w-4 mr-1" />
            <span>{repo.forks_count}</span>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={() => window.open(repo.html_url, '_blank')} className="bg-black text-white hover:bg-gray-700 border-gray-700">
            <ExternalLink className="h-4 w-4" />
          </Button>
          <Button size="sm" onClick={handleOpenInBeetle} className="bg-orange-500 text-black hover:bg-orange-600">
            Open in GitMesh
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
};