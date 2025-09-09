import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function OrganizationCard({ org }: { org: any }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center space-x-4">
        <Avatar>
          <AvatarImage src={org.avatar_url} alt={org.login} />
          <AvatarFallback>{org.login.charAt(0)}</AvatarFallback>
        </Avatar>
        <div>
          <CardTitle>{org.login}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <a href={org.html_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
          View on GitHub
        </a>
      </CardContent>
    </Card>
  );
}
