
import { Input } from '@/components/ui/input';

interface SearchBarProps {
  onSearch: (query: string) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch }) => (
  <Input
    type="text"
    placeholder="Search projects..."
    onChange={(e) => onSearch(e.target.value)}
    className="w-full bg-gray-800 border-gray-700 text-white placeholder-gray-500 rounded-lg focus:ring-orange-500 focus:border-orange-500"
  />
);
