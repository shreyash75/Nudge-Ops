-- Baseline schema for NudgeOps self-managed PostgreSQL.
-- Applied automatically on first container start (docker-entrypoint-initdb.d)
-- and also at backend startup via SQLAlchemy (idempotent).
-- Ownership is enforced in application code: every query filters by user_id.

create table if not exists app_users (
  id varchar(36) primary key,
  email varchar(320) not null unique,
  password_hash text not null,
  created_at timestamptz not null default now()
);

create table if not exists investigation_history (
  id varchar(36) primary key,
  user_id varchar(36) not null,
  cluster varchar(253),
  status varchar(64) not null,
  message text,
  root_cause text,
  namespace varchar(255),
  explanation text,
  confidence integer check (confidence between 0 and 100),
  investigation jsonb not null default '{}'::jsonb,
  diagnosis jsonb,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists investigation_history_user_created_idx
  on investigation_history (user_id, created_at desc);
