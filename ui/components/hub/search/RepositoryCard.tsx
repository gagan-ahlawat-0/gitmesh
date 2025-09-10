import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { GitFork, Star, Users, ExternalLink } from "lucide-react";
import { useRouter } from "next/navigation";

export function RepositoryCard({ repo }: { repo: any }) {
  const router = useRouter();

  const handleOpenInBeetle = () => {
    const repoData = JSON.stringify(repo);
    const encodedRepo = encodeURIComponent(repoData);
    router.push(`/contribution?repo=${encodedRepo}`);
  };

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <CardTitle>{repo.name}</CardTitle>
        <CardDescription>{repo.description}</CardDescription>
      </CardHeader>
      <CardContent className="flex-grow">
        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
          <div className="flex items-center">
            <Star className="mr-1 h-3 w-3" />
            {repo.stargazers_count}
          </div>
          <div className="flex items-center">
            <GitFork className="mr-1 h-3 w-3" />
            {repo.forks_count}
          </div>
          <div className="flex items-center">
            <Users className="mr-1 h-3 w-3" />
            {repo.watchers_count}
          </div>
        </div>
      </CardContent>
      <CardFooter className="flex justify-between items-center space-x-2">
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
