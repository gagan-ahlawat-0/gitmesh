import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function UserCard({ user }: { user: any }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center space-x-4">
        <Avatar>
          <AvatarImage src={user.avatar_url} alt={user.login} />
          <AvatarFallback>{user.login.charAt(0)}</AvatarFallback>
        </Avatar>
        <div>
          <CardTitle>{user.login}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <a href={user.html_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
          View on GitHub
        </a>
      </CardContent>
    </Card>
  );
}
