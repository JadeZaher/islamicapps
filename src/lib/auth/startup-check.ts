/** Node-only start-up check: exit when private preview is on without working curator sign-in. */
import { previewConfigurationProblem } from './switches';

export function refuseUnsafePreview(): void {
  const problem = previewConfigurationProblem();
  if (!problem) return;
  console.error(`Refusing to start: ${problem}`);
  process.exit(1);
}
