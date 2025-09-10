import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { GitHubUser } from "@/lib/types";
import { ExternalLink, MapPin, Link, Calendar, Building, Mail, Users, UserPlus, UserMinus } from "lucide-react";

interface ProfileHeaderProps {
  user: GitHubUser;
  isOwnProfile: boolean;
  isFollowing: boolean;
  onFollowToggle: () => void;
}

export function ProfileHeader({ user, isOwnProfile, isFollowing, onFollowToggle }: ProfileHeaderProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric'
    });
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 p-6 border rounded-lg">
      {/* Avatar */}
      <div className="flex-shrink-0">
        <Avatar className="w-32 h-32">
          <AvatarImage src={user.avatar_url} alt={user.name || user.login} />
          <AvatarFallback className="text-2xl">
            {(user.name || user.login).charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
      </div>

      {/* User Info */}
      <div className="flex-1 space-y-4">
        {/* Name and Username */}
        <div className="space-y-1">
          <h1 className="text-3xl font-bold">{user.name || user.login}</h1>
          <p className="text-xl text-muted-foreground">@{user.login}</p>
          {user.bio && (
            <p className="text-base text-foreground mt-2">{user.bio}</p>
          )}
          
          {/* Organizations */}
          {user.organizations && user.organizations.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-medium text-muted-foreground mb-2">Organizations</p>
              <div className="flex flex-wrap gap-2">
                {user.organizations.map((org) => (
                  <a
                    key={org.id}
                    href={org.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-3 py-1 bg-muted rounded-full hover:bg-muted/80 transition-colors"
                    title={org.name || org.login}
                  >
                    <Avatar className="w-5 h-5">
                      <AvatarImage src={org.avatar_url} alt={org.login} />
                      <AvatarFallback className="text-xs">
                        {org.login.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <span className="text-sm">{org.login}</span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User Details */}
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          {user.company && (
            <div className="flex items-center gap-1">
              <Building className="w-4 h-4" />
              <span>{user.company}</span>
            </div>
          )}
          {user.location && (
            <div className="flex items-center gap-1">
              <MapPin className="w-4 h-4" />
              <span>{user.location}</span>
            </div>
          )}
          {user.blog && (
            <div className="flex items-center gap-1">
              <Link className="w-4 h-4" />
              <a 
                href={user.blog.startsWith('http') ? user.blog : `https://${user.blog}`} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline"
              >
                {user.blog}
              </a>
            </div>
          )}
          {user.email && (
            <div className="flex items-center gap-1">
              <Mail className="w-4 h-4" />
              <span>{user.email}</span>
            </div>
          )}
          <div className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            <span>Joined {formatDate(user.created_at)}</span>
          </div>
        </div>

        {/* Stats */}
        <div className="flex space-x-6">
          <div className="flex items-center gap-1">
            <Users className="w-4 h-4" />
            <span className="font-semibold">{user.followers}</span>
            <span className="text-muted-foreground">followers</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="font-semibold">{user.following}</span>
            <span className="text-muted-foreground">following</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="font-semibold">{user.public_repos}</span>
            <span className="text-muted-foreground">repositories</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-4">
          {!isOwnProfile && (
            <Button 
              onClick={onFollowToggle}
              variant={isFollowing ? "outline" : "default"}
              className="flex items-center gap-2"
            >
              {isFollowing ? (
                <>
                  <UserMinus className="w-4 h-4" />
                  Unfollow
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
                  Follow
                </>
              )}
            </Button>
          )}
          <Button 
            variant="outline" 
            onClick={() => window.open(user.html_url, '_blank')}
            className="flex items-center gap-2"
          >
            <ExternalLink className="w-4 h-4" />
            View on GitHub
          </Button>
        </div>

        {/* Achievements (placeholder for now) */}
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">GitHub User</Badge>
          {user.public_repos > 10 && <Badge variant="secondary">Prolific Contributor</Badge>}
          {user.followers > 50 && <Badge variant="secondary">Popular Developer</Badge>}
          {new Date().getFullYear() - new Date(user.created_at).getFullYear() >= 5 && (
            <Badge variant="secondary">Veteran Developer</Badge>
          )}
        </div>
      </div>
    </div>
  );
}
