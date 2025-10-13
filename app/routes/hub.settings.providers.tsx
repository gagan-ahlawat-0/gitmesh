import CloudProvidersTab from '~/components/@settings/tabs/providers/cloud/CloudProvidersTab';
import LocalProvidersTab from '~/components/@settings/tabs/providers/local/LocalProvidersTab';

export default function HubSettingsProviders() {
  return (
    <div className="p-6 space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-gitmesh-elements-textPrimary mb-6">AI Model Providers</h2>

        <div className="space-y-8">
          <div>
            <h3 className="text-md font-medium text-gitmesh-elements-textPrimary mb-4">Cloud Providers</h3>
            <CloudProvidersTab />
          </div>

          <div className="border-t border-gitmesh-elements-borderColor pt-8">
            <h3 className="text-md font-medium text-gitmesh-elements-textPrimary mb-4">Local Providers</h3>
            <LocalProvidersTab />
          </div>
        </div>
      </div>
    </div>
  );
}
