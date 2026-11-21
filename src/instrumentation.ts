/** Server start-up checks (Node runtime only). See src/lib/auth/AGENTS.md §Switches. */
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { refuseUnsafePreview } = await import('./lib/auth/startup-check');
    refuseUnsafePreview();
  }
}
