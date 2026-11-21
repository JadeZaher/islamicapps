/** Minimal sequential flow-test runner in the repo's tsx convention: PASS/FAIL lines, exit code 1 on any failure. */

interface Flow {
  name: string;
  run: () => Promise<void>;
}

const flows: Flow[] = [];

export function flow(name: string, run: () => Promise<void>): void {
  flows.push({ name, run });
}

/** Runs every registered flow in order, then `teardown`, and sets the exit code. */
export async function runFlows(teardown?: () => Promise<void>): Promise<void> {
  let failed = 0;
  for (const { name, run } of flows) {
    const started = performance.now();
    try {
      await run();
      console.log(`  PASS ${name} (${Math.round(performance.now() - started)} ms)`);
    } catch (error) {
      failed++;
      console.log(`  FAIL ${name}\n    ${error instanceof Error ? error.stack ?? error.message : String(error)}`);
    }
  }
  if (teardown) await teardown();
  console.log(`\n${flows.length - failed} passed, ${failed} failed`);
  process.exitCode = failed > 0 ? 1 : 0;
}

/** Awaits a promise expected to reject; returns the error for assertions. */
export async function rejection(promise: Promise<unknown>): Promise<Error & { code?: string }> {
  try {
    await promise;
  } catch (error) {
    return error as Error & { code?: string };
  }
  throw new Error('Expected the call to be refused, but it succeeded.');
}
