import { json, type MetaFunction } from '@remix-run/cloudflare';
import LandingPage from '~/components/landing/LandingPage';

export const meta: MetaFunction = () => {
  return [{ title: 'GitMesh' }, { name: 'description', content: 'GitMesh: Git Collaboration Network for OSS' }];
};

export const loader = () => json({});

/**
 * Main landing page with authentication
 */
export default function Index() {
  return <LandingPage />;
}
