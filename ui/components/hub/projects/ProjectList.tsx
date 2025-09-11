
import { useState } from 'react';
import { Repository } from '@/lib/github-api';
import { ProjectCard } from './ProjectCard';
import { Button } from '@/components/ui/button';

interface ProjectListProps {
  projects: Repository[];
}

const ITEMS_PER_PAGE = 6;

export const ProjectList: React.FC<ProjectListProps> = ({ projects }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const totalPages = Math.ceil(projects.length / ITEMS_PER_PAGE);

  const paginatedProjects = projects.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {paginatedProjects.map((project) => (
          <ProjectCard key={project.id} repo={project} />
        ))}
      </div>
      {totalPages > 1 && (
        <div className="flex justify-center mt-8">
          <Button
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            className="bg-orange-500 text-black hover:bg-orange-600 disabled:bg-gray-700"
          >
            Previous
          </Button>
          <span className="mx-4 text-white">Page {currentPage} of {totalPages}</span>
          <Button
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            className="bg-orange-500 text-black hover:bg-orange-600 disabled:bg-gray-700"
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
};
