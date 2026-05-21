// Verifies NEXT_PUBLIC_SUPABASE_URL + NEXT_PUBLIC_SUPABASE_ANON_KEY reach a live project.
// Passing a dummy JWT to auth.getUser() forces a real HTTP GET to /auth/v1/user with
// Authorization header — the server validates the token and returns 401, which proves
// the endpoint is reachable. Calling auth.getUser() without an arg only inspects the
// local session and never hits the network in current @supabase/supabase-js.
// process.loadEnvFile() is Node 20.6+ built-in — needed because tsx alone does not load .env files.
process.loadEnvFile('.env.local');

async function main(): Promise<void> {
  const { supabase } = await import('../lib/supabase/client');
  const { data, error } = await supabase.auth.getUser('dummy-jwt-to-force-server-roundtrip');
  if (error && error.status !== 401 && error.status !== 403) {
    throw error;
  }
  console.log('Supabase reachable. user:', data.user);
}

main().catch((err) => {
  console.error('Supabase connection check FAILED:', err);
  process.exit(1);
});
