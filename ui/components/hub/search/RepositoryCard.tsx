import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { GitFork, Star, Users } from "lucide-react";

export function RepositoryCard({ repo }: { repo: any }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{repo.name}</CardTitle>
        <CardDescription>{repo.description}</CardDescription>
      </CardHeader>
      <CardContent>
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
      <CardFooter>
        <a href={repo.html_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
          View on GitHub
        </a>
      </CardFooter>
    </Card>
  );
}
