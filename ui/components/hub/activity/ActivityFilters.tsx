
"use client";

import { useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { DateRangePicker } from "@/components/ui/date-range-picker";

interface ActivityFiltersProps {
  repositories: any[];
  onFilterChange: (filters: any) => void;
}

export const ActivityFilters: React.FC<ActivityFiltersProps> = ({ repositories, onFilterChange }) => {
  const [selectedRepo, setSelectedRepo] = useState("all");
  const [dateRange, setDateRange] = useState<any>(null);

  const handleFilterChange = () => {
    onFilterChange({ repository: selectedRepo, dateRange });
  };

  return (
    <div className="flex flex-col md:flex-row items-center gap-4">
      <Select onValueChange={setSelectedRepo} defaultValue="all">
        <SelectTrigger className="w-full md:w-[280px] bg-black border-gray-700 text-white rounded-lg focus:ring-orange-500 focus:border-orange-500">
          <SelectValue placeholder="Select a repository" />
        </SelectTrigger>
        <SelectContent className="bg-black text-white border-gray-700">
          <SelectItem value="all">All Repositories</SelectItem>
          {repositories.map((repo) => (
            <SelectItem key={repo.id} value={repo.full_name}>
              {repo.full_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <DateRangePicker onRangeChange={setDateRange} />
      <Button onClick={handleFilterChange} className="w-full md:w-auto bg-orange-500 text-black hover:bg-orange-600">Apply Filters</Button>
    </div>
  );
};
