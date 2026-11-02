-- Investigation history owners are FastAPI-managed accounts.
-- The original foreign key tied investigation_history.user_id to
-- auth.users(id), which forced every backend user to also exist as an
-- InsForge Auth account. Backend-managed user IDs are plain UUIDs that have
-- no InsForge Auth counterpart, so the FK is no longer valid.
-- Owner-only RLS policies below remain in force and unchanged.
alter table public.investigation_history
  drop constraint if exists investigation_history_user_id_fkey;
