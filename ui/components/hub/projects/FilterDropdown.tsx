import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface FilterDropdownProps {
  onFilterChange: (value: string) => void;
  languages: string[];
}

export const FilterDropdown: React.FC<FilterDropdownProps> = ({ onFilterChange, languages }) => (
  <Select onValueChange={onFilterChange}>
    <SelectTrigger className="w-full bg-black border-gray-700 text-white rounded-lg focus:ring-orange-500 focus:border-orange-500">
      <SelectValue placeholder="Filter by..." />
    </SelectTrigger>
    <SelectContent className="bg-black text-white border-gray-700">
      <SelectItem value="all" className="hover:bg-gray-700">All</SelectItem>
      <SelectItem value="owner" className="hover:bg-gray-700">Owned</SelectItem>
      <SelectItem value="member" className="hover:bg-gray-700">Contributed</SelectItem>
      <SelectItem value="fork" className="hover:bg-gray-700">Forked</SelectItem>
      {languages.map((lang) => (
        <SelectItem key={lang} value={lang} className="hover:bg-gray-700">{
          lang
        }</SelectItem>
      ))}
    </SelectContent>
  </Select>
);