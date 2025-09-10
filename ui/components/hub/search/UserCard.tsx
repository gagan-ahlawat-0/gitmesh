import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ExternalLink, User } from "lucide-react";
import { useRouter } from "next/navigation";

export function UserCard({ user }: { user: any }) {
  const router = useRouter();

  const handleViewProfile = () => {
    router.push(`/hub/profile/${user.login}`);
  };

  return (
    <Card className="flex flex-col">
      <CardHeader className="flex flex-row items-center space-x-4">
        <Avatar>
          <AvatarImage src={user.avatar_url} alt={user.login} />
          <AvatarFallback>{user.login.charAt(0)}</AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <CardTitle>{user.name || user.login}</CardTitle>
          <p className="text-sm text-muted-foreground">@{user.login}</p>
        </div>
      </CardHeader>
      <CardContent className="flex-grow">
        {user.bio && (
          <p className="text-sm text-muted-foreground mb-2">{user.bio}</p>
        )}
        <div className="flex items-center space-x-4 text-xs text-muted-foreground">
          {user.followers !== undefined && (
            <span>{user.followers} followers</span>
          )}
          {user.public_repos !== undefined && (
            <span>{user.public_repos} repos</span>
          )}
        </div>
      </CardContent>
      <CardFooter className="flex justify-between items-center space-x-2">
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => window.open(user.html_url, '_blank')}
          className="flex items-center space-x-1"
        >
          <ExternalLink className="h-3 w-3" />
          <span>GitHub</span>
        </Button>
        <Button 
          size="sm" 
          onClick={handleViewProfile}
          className="flex items-center space-x-1"
        >
          <User className="h-3 w-3" />
          <span>View Profile</span>
        </Button>
      </CardFooter>
    </Card>
  );
}
