/** Server start-up checks (Node runtime only). See src/lib/auth/AGENTS.md §Switches and src/lib/AGENTS.md §Site origin. */
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { startupProblems } = await import('./lib/auth/startup-check');
    const problems = startupProblems();
    if (problems.length === 0) return;
    for (const problem of problems) console.error(`Refusing to start: ${problem}`);
    process.exit(1);
  }
}
