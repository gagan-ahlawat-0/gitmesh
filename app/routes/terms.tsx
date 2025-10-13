import { json, type MetaFunction } from '@remix-run/cloudflare';
import { Link } from '@remix-run/react';
import BackgroundRays from '~/components/ui/BackgroundRays';
import { Button } from '~/components/ui/Button';

export const meta: MetaFunction = () => {
  return [
    { title: 'Terms of Service - GitMesh' },
    { name: 'description', content: 'Terms of Service for GitMesh - Git Collaboration Network' },
  ];
};

export const loader = () => json({});

export default function Terms() {
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
              <h1 className="text-3xl font-bold text-gitmesh-elements-textPrimary mb-2">Terms of Service</h1>
              <p className="text-gitmesh-elements-textSecondary">Last updated: {new Date().toLocaleDateString()}</p>
            </div>

            {/* Terms Content */}
            <div className="prose prose-invert max-w-none space-y-6">
              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">1. Acceptance of Terms</h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  By accessing and using GitMesh ("the Service"), you accept and agree to be bound by the terms and
                  provision of this agreement. If you do not agree to abide by the above, please do not use this
                  service.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  2. Description of Service
                </h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  GitMesh is a Git Collaboration Network for Open Source Software (OSS) that provides tools and services
                  for managing and collaborating on software projects. The Service includes but is not limited to
                  repository management, integration with GitHub and GitLab, project analytics, and collaboration
                  features.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">3. User Accounts</h2>
                <div className="text-gitmesh-elements-textSecondary leading-relaxed space-y-2">
                  <p>
                    When creating an account with us, you must provide information that is accurate, complete, and
                    current at all times. You are responsible for:
                  </p>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>Safeguarding your account credentials</li>
                    <li>All activities that occur under your account</li>
                    <li>Notifying us immediately of any unauthorized use of your account</li>
                  </ul>
                </div>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  4. Acceptable Use Policy
                </h2>
                <div className="text-gitmesh-elements-textSecondary leading-relaxed space-y-2">
                  <p>You agree not to use the Service to:</p>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>
                      Upload, transmit, or distribute any content that is illegal, harmful, or violates others' rights
                    </li>
                    <li>Attempt to gain unauthorized access to the Service or its related systems</li>
                    <li>Interfere with or disrupt the integrity or performance of the Service</li>
                    <li>Use the Service for any commercial purposes without explicit permission</li>
                    <li>Violate any applicable local, state, national, or international law</li>
                  </ul>
                </div>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  5. Privacy and Data Protection
                </h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  Your privacy is important to us. We collect and use your personal information in accordance with our
                  Privacy Policy. By using the Service, you consent to the collection and use of your information as
                  described in our Privacy Policy.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  6. Intellectual Property Rights
                </h2>
                <div className="text-gitmesh-elements-textSecondary leading-relaxed space-y-2">
                  <p>
                    The Service and its original content, features, and functionality are owned by GitMesh and are
                    protected by international copyright, trademark, patent, trade secret, and other intellectual
                    property laws.
                  </p>
                  <p>
                    You retain ownership of any content you submit, post, or display through the Service, but you grant
                    us a license to use, modify, and display such content for the purpose of providing the Service.
                  </p>
                </div>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  7. Third-Party Integrations
                </h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  GitMesh integrates with third-party services such as GitHub and GitLab. Your use of these integrations
                  is subject to the respective terms of service of those platforms. We are not responsible for the
                  availability or content of these third-party services.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  8. Service Availability
                </h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  We strive to maintain high availability of the Service but do not guarantee uninterrupted access. The
                  Service may be temporarily unavailable due to maintenance, updates, or circumstances beyond our
                  control.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  9. Limitation of Liability
                </h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  In no event shall GitMesh, its directors, employees, partners, agents, suppliers, or affiliates be
                  liable for any indirect, incidental, punitive, consequential, or similar damages arising out of your
                  use of the Service.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">10. Termination</h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  We may terminate or suspend your account and bar access to the Service immediately, without prior
                  notice or liability, under our sole discretion, for any reason whatsoever, including but not limited
                  to a breach of the Terms.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">11. Changes to Terms</h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  We reserve the right to modify or replace these Terms at any time. If a revision is material, we will
                  provide at least 30 days notice prior to any new terms taking effect.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-3">
                  12. Contact Information
                </h2>
                <p className="text-gitmesh-elements-textSecondary leading-relaxed">
                  If you have any questions about these Terms of Service, please contact us at:
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
