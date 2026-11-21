/** Node-only start-up refusals (src/instrumentation.ts): unsafe private preview; missing or unsafe SITE_URL in production. */
import { siteUrlProblem } from '../site-origin';
import { previewConfigurationProblem } from './switches';

/** Every reason the server must not start; empty when it may. */
export function startupProblems(env: NodeJS.ProcessEnv = process.env): string[] {
  const problems: string[] = [];
  const preview = previewConfigurationProblem();
  if (preview) problems.push(preview);
  if (env.NODE_ENV === 'production') {
    const site = siteUrlProblem(env.SITE_URL);
    if (site) problems.push(site);
  }
  return problems;
}
