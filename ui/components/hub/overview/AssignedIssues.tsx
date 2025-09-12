
import { useState } from 'react';
import { Issue, PullRequest } from '@/lib/github-api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface AssignedIssuesProps {
  issues: Issue[];
  pullRequests: PullRequest[];
}

const ITEMS_PER_PAGE = 5;

export const AssignedIssues: React.FC<AssignedIssuesProps> = ({ issues, pullRequests }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const items = [...(issues || []), ...(pullRequests || [])].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  const totalPages = Math.ceil(items.length / ITEMS_PER_PAGE);

  const paginatedItems = items.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  return (
    <Card className="bg-black shadow-lg rounded-lg h-[400px] flex flex-col">
      <CardHeader>
        <CardTitle className="text-xl font-bold text-gray-200">Assigned to You</CardTitle>
      </CardHeader>
      <CardContent className="flex-grow overflow-y-auto">
        <ul className="space-y-4">
          {paginatedItems.map((item) => (
            <li key={item.id} className="p-4 bg-black rounded-lg shadow-sm">
              <div className="flex justify-between items-center">
                <div>
                  <a href={item.html_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-orange-400 hover:underline">
                    {item.title}
                  </a>
                  <p className="text-sm text-gray-400">
                    #{item.number} in {item.repository_url?.split('/').slice(-2).join('/') || 'unknown repo'}
                  </p>
                </div>
                <span
                  className={`px-3 py-1 text-xs font-bold rounded-full ${
                    'labels' in item ? 'bg-red-900 text-red-200' : 'bg-green-900 text-green-200'
                  }`}>
                  {'labels' in item ? 'Issue' : 'Pull Request'}
                </span>
              </div>
              {'labels' in item && (item.labels.length > 0) && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {item.labels.map((label: any) => (
                    <span key={label.id} className="px-2 py-1 text-xs font-semibold rounded-full text-white" style={{ backgroundColor: `#${label.color}` }}>
                      {label.name}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      </CardContent>
      {totalPages > 1 && (
        <div className="flex justify-center mt-6 mb-4">
          <Button
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            className="bg-orange-500 text-black hover:bg-orange-600 disabled:bg-gray-700"
          >
            Previous
          </Button>
          <span className="mx-4 text-gray-300">Page {currentPage} of {totalPages}</span>
          <Button
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            className="bg-orange-500 text-black hover:bg-orange-600 disabled:bg-gray-700"
          >
            Next
          </Button>
        </div>
      )}
    </Card>
  );
};
