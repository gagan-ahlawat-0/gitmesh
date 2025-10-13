import { HubProjectsView } from '~/components/hub/HubProjectsView';

export default function HubProjects() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gitmesh-elements-textPrimary mb-4">Projects</h1>
      <p className="text-gitmesh-elements-textSecondary mb-8">
        Manage and explore your repositories across GitHub and GitLab.
      </p>

      <HubProjectsView />
    </div>
  );
}
