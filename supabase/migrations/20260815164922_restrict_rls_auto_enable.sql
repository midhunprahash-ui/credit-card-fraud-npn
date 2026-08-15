-- Supabase's automatic-RLS helper is an internal SECURITY DEFINER function.
-- Keep it unavailable through the public Data API RPC endpoint.
revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
