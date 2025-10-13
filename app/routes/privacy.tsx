import { json, type MetaFunction } from '@remix-run/cloudflare';
import { Link } from '@remix-run/react';
import BackgroundRays from '~/components/ui/BackgroundRays';
import { Button } from '~/components/ui/Button';

export const meta: MetaFunction = () => {
  return [
    { title: 'Privacy Policy - GitMesh' },
    { name: 'description', content: 'Privacy Policy for GitMesh - Git Collaboration Network' },
  ];
};

export const loader = () => json({});

export default function Privacy() {
  return (
    <div className="min-h-screen bg-gitmesh-elements-background-depth-1">
      <BackgroundRays />

      {/* Header */}
      <header className="relative z-10 border-b border-gitmesh-elements-borderColor">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-gitmesh-elements-button-primary-background to-gitmesh-elements-button-primary-backgroundHover rounded-lg flex items-center justify-center">
                <div className="i-ph:git-branch-duotone text-white" />
              </div>
              <span className="text-xl font-semibold text-gitmesh-elements-textPrimary">GitMesh</span>
            </Link>
            <Link to="/">
              <Button variant="outline" size="sm">
                <div className="i-ph:arrow-left w-4 h-4 mr-2" />
                Back to Home
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-4xl mx-auto px-6 py-12">
        <div className="bg-gitmesh-elements-background-depth-1 rounded-lg border border-gitmesh-elements-borderColor p-8">
          <div className="space-y-8">
            {/* Title */}
            <div className="text-center">
              <h1 className="text-3xl font-bold text-gitmesh-elements-textPrimary mb-2">Privacy Policy</h1>
              <p className="text-gitmesh-elements-textSecondary">Last updated: {new Date().toLocaleDateString()}</p>
            </div>

            {/* Privacy Content */}
            <div className="prose prose-invert max-w-none space-y-6">
              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  1. Information We Collect
                </h2>
                <div className="text-gitmesh-elements-textSecondary leading-relaxed space-y-2">
                  <p>We collect information you provide directly to us, such as when you:</p>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>Create an account</li>
                    <li>Connect your GitHub or GitLab accounts</li>
                    <li>Use our services and features</li>
                    <li>Contact us for support</li>
                  </ul>
                </div>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  2. How We Use Your Information
                </h2>
                <div className="text-gitmesh-elements-textSecondary leading-relaxed space-y-2">
                  <p>We use the information we collect to:</p>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>Provide, maintain, and improve our services</li>
                    <li>Process transactions and send related information</li>
                    <li>Send technical notices and support messages</li>
                    <li>Monitor and analyze trends and usage</li>
                    <li>Detect and prevent fraud and abuse</li>
                  </ul>
                </div>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">3. Information Sharing</h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  We do not sell, trade, or otherwise transfer your personal information to third parties without your
                  consent, except as described in this policy. We may share your information in the following
                  circumstances:
                </p>
                <ul className="list-disc list-inside ml-4 space-y-1 mt-2 text-gitmesh-elements-textSecondary">
                  <li>With your explicit consent</li>
                  <li>To comply with legal obligations</li>
                  <li>To protect our rights and safety</li>
                  <li>With service providers who assist our operations</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">4. Data Security</h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  We implement appropriate technical and organizational security measures to protect your personal
                  information against unauthorized access, alteration, disclosure, or destruction.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  5. Third-Party Integrations
                </h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  Our service integrates with GitHub and GitLab. When you connect these accounts, we access only the
                  information necessary to provide our services. Please review the privacy policies of these third-party
                  services as well.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">6. Your Rights</h2>
                <div className="text-gitmesh-elements-textSecondary leading-relaxed space-y-2">
                  <p>You have the right to:</p>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>Access your personal information</li>
                    <li>Correct inaccurate information</li>
                    <li>Delete your personal information</li>
                    <li>Restrict processing of your information</li>
                    <li>Data portability</li>
                  </ul>
                </div>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">7. Contact Us</h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  If you have any questions about this Privacy Policy, please contact us:
                </p>
                <div className="mt-2 p-4 bg-gitmesh-elements-background-depth-1 border border-gitmesh-elements-borderColor rounded-lg">
                  <p className="text-gitmesh-elements-textPrimary font-medium">GitMesh Support</p>
                  <p className="text-gitmesh-elements-textSecondary">Email: support@gitmesh.dev</p>
                  <p className="text-gitmesh-elements-textSecondary">Website: https://www.gitmesh.dev</p>
                </div>
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
