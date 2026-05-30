---
name: postgres-best-practices
description: Use when writing, reviewing, or optimizing PostgreSQL on Supabase — designing indexes (btree/gin/partial/covering), reading EXPLAIN ANALYZE, fixing slow or N+1 queries, configuring connection pooling (Supavisor/PgBouncer), paginating large tables, running zero-downtime schema migrations (NOT VALID constraints, CREATE INDEX CONCURRENTLY, batched backfills, expand/contract), or implementing Row Level Security policies with auth.uid(). Trigger on mentions of EXPLAIN, slow query, missing index, lock timeout, blocking migration, ALTER TABLE on a big table, RLS, "policy", connection limit, "too many connections", or keyset/offset pagination.
---

# Postgres Best Practices (Supabase)

Source: Supabase — https://mcpservers.org/agent-skills/supabase/postgres-best-practices
Reference docs: https://supabase.com/docs/guides/database , https://supabase.com/docs/guides/database/postgres/row-level-security

This skill covers three scopes: **PERFORMANCE**, **ZERO-DOWNTIME MIGRATIONS**, and **RLS (Row Level Security)**. Apply the relevant scope; do not dump all three on every task. Always prove a change with `EXPLAIN ANALYZE` or a benchmark rather than guessing.

---

## How to work

1. Identify the scope: is this a slow query (PERFORMANCE), a schema change on a live table (MIGRATIONS), or access control (RLS)?
2. Measure first. For performance, run `EXPLAIN (ANALYZE, BUFFERS)` before changing anything. For migrations, check the table size and current locks. For RLS, test the policy as both an authenticated and an anonymous role.
3. Make the smallest correct change, then re-measure.
4. Never run a blocking DDL on a large hot table without a `lock_timeout` guard.
5. Never disable RLS to "fix" a query — fix the policy instead.

---

## SCOPE 1 — PERFORMANCE

### 1.1 EXPLAIN ANALYZE — always measure

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders WHERE customer_id = 42 ORDER BY created_at DESC LIMIT 20;
```

Read it bottom-up. Red flags:
- `Seq Scan` on a large table where you filter/join → missing or unusable index.
- `Rows Removed by Filter: <large>` → the index isn't selective; consider a partial or composite index.
- Estimated rows wildly different from actual rows → stale statistics; run `ANALYZE <table>;`.
- `Nested Loop` with high loop count over a large inner relation → often an N+1 or a missing join index.
- High `Buffers: shared read=...` → reading from disk, not cache; the working set or index may be too large.

Use `EXPLAIN (ANALYZE, BUFFERS)` (it actually executes the query). Use plain `EXPLAIN` when you must not run side effects (e.g. an `UPDATE`).

### 1.2 Indexing strategy

**B-tree (default)** — equality and range on scalar columns, and `ORDER BY`.
```sql
CREATE INDEX idx_orders_customer ON orders (customer_id);
```

**Composite / multi-column** — order matters. Put the equality column first, the range/sort column last. This index serves `WHERE customer_id = ? ORDER BY created_at DESC`:
```sql
CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at DESC);
```

**Partial index** — index only the rows you query, smaller and faster. Great for soft-delete or status flags:
```sql
CREATE INDEX idx_orders_open ON orders (customer_id)
WHERE status = 'open';
```

**Covering index (INCLUDE)** — lets Postgres satisfy a query from the index alone (`Index Only Scan`), skipping the heap fetch:
```sql
CREATE INDEX idx_orders_cover ON orders (customer_id) INCLUDE (status, total_cents);
```

**GIN** — for `jsonb`, arrays, and full-text search.
```sql
-- jsonb containment (@>, ?, ?&)
CREATE INDEX idx_events_payload ON events USING gin (payload jsonb_path_ops);
-- full-text search
CREATE INDEX idx_articles_fts ON articles USING gin (to_tsvector('english', body));
-- trigram fuzzy / ILIKE search (requires pg_trgm)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_users_name_trgm ON users USING gin (name gin_trgm_ops);
```

Guidance:
- Don't over-index. Every index slows down `INSERT`/`UPDATE`/`DELETE` and costs storage.
- A column used only in `WHERE col = const` with one value almost never needs its own index — a partial index on the *other* filter is usually better.
- Find unused indexes: query `pg_stat_user_indexes` for `idx_scan = 0`.
- Find duplicate/redundant indexes before adding new ones.

### 1.3 Avoiding N+1 queries

N+1 = one query for a list, then one extra query per row. Fix by fetching in a single set-based query.

```sql
-- BAD: app loops over orders and runs this per order
SELECT * FROM order_items WHERE order_id = $1;

-- GOOD: one round trip
SELECT o.id, o.total_cents,
       json_agg(i.*) AS items
FROM orders o
LEFT JOIN order_items i ON i.order_id = o.id
WHERE o.customer_id = $1
GROUP BY o.id;
```

In the Supabase JS client, use embedded resources instead of looping:
```js
// one request, joined via FK relationship
const { data } = await supabase
  .from('orders')
  .select('id, total_cents, order_items(*)')
  .eq('customer_id', 42);
```

### 1.4 Connection pooling (Supavisor / PgBouncer)

Postgres has a hard `max_connections` limit; serverless/edge functions open and drop connections constantly and will exhaust it. Route app traffic through a pooler, not the direct `5432` database connection.

Supabase provides:
- **Supavisor (Shared Pooler)** — available on all tiers, IPv4-capable. Use the `*.pooler.supabase.com` host.
- **PgBouncer (Dedicated Pooler)** — paid plans, co-located with the database.

Two modes:
- **Transaction mode — port `6543`.** Best for serverless / edge functions / many short-lived connections. A server connection is assigned per transaction. **Does NOT support prepared statements** — disable them in your client library (e.g. `prepare: false` / `statement_cache_size=0`), or you'll get errors.
- **Session mode — port `5432` (pooler host).** Best for long-lived backend processes that need session features (prepared statements, `SET`, advisory locks held across statements, `LISTEN/NOTIFY`).

```text
# Transaction mode (serverless) — note port 6543
postgres://postgres.<project-ref>:[PASSWORD]@aws-<region>.pooler.supabase.com:6543/postgres

# Session mode (persistent backend) — pooler host, port 5432
postgres://postgres.<project-ref>:[PASSWORD]@aws-<region>.pooler.supabase.com:5432/postgres
```

Rule of thumb: serverless → transaction mode (6543) with prepared statements off; a single long-running backend / migration tool → session mode or direct connection.

### 1.5 Pagination — keyset vs offset

**OFFSET pagination is O(n)** — Postgres still scans and discards every skipped row. Page 10,000 of a feed gets progressively slower and can also skip/duplicate rows when data changes underneath.

```sql
-- BAD on deep pages: scans 200020 rows to return 20
SELECT * FROM posts ORDER BY created_at DESC, id DESC
OFFSET 200000 LIMIT 20;
```

**Keyset (cursor) pagination** is O(log n) on an index and stable. Carry the last row's sort key forward:

```sql
-- First page
SELECT * FROM posts
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- Next page: pass the last row's (created_at, id) as the cursor.
-- Row-value comparison handles ties correctly.
SELECT * FROM posts
WHERE (created_at, id) < ($1, $2)   -- $1 = last created_at, $2 = last id
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

Back this with a composite index matching the sort: `CREATE INDEX idx_posts_feed ON posts (created_at DESC, id DESC);`

Use OFFSET only for shallow, bounded paging (e.g. an admin table of a few hundred rows). Use keyset for infinite scroll, feeds, and exports.

---

## SCOPE 2 — ZERO-DOWNTIME MIGRATIONS

Principle: a schema change must be safe to run while the old app code is still serving traffic and while the new code rolls out. Avoid long `ACCESS EXCLUSIVE` locks on hot tables.

### 2.1 Lock-timeout safety wrapper

Always cap how long a migration may block. Without this, one DDL statement queued behind a long read can stall every query on the table.

```sql
SET lock_timeout = '5s';
SET statement_timeout = '0';  -- but keep lock_timeout finite
-- ... your DDL ...
```

If the DDL can't acquire its lock within 5s it errors out instead of freezing production; retry during a quieter window.

### 2.2 Additive-first

Prefer changes that don't touch existing rows or rewrite the table:
- **Adding a nullable column** is instant (metadata only) in modern Postgres.
- **Adding a column with a non-volatile DEFAULT** is also fast (Postgres 11+ stores it as metadata, no table rewrite).
- **Avoid** changing a column type in place on a big table — it rewrites and takes an `ACCESS EXCLUSIVE` lock. Instead use expand/contract (2.6).

```sql
-- Safe: nullable add
ALTER TABLE orders ADD COLUMN notes text;

-- Safe in PG 11+: constant default, no rewrite
ALTER TABLE orders ADD COLUMN currency text NOT NULL DEFAULT 'USD';
```

### 2.3 CREATE INDEX CONCURRENTLY

A plain `CREATE INDEX` takes a lock that blocks writes for the whole build. Use `CONCURRENTLY` on live tables — it builds without blocking writes.

```sql
-- NOTE: cannot run inside a transaction block.
-- Run it standalone (most migration tools support a "no transaction" flag).
CREATE INDEX CONCURRENTLY idx_orders_customer ON orders (customer_id);
```

Caveats:
- It is slower and can fail leaving an `INVALID` index. Detect and clean up:
```sql
SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;
DROP INDEX CONCURRENTLY idx_orders_customer;  -- then recreate
```
- Use `DROP INDEX CONCURRENTLY` to remove an index without blocking.

### 2.4 NOT VALID constraints, then VALIDATE

Adding a `CHECK` or `FOREIGN KEY` normally scans the whole table under a strong lock. Split it into two cheap steps:

```sql
-- Step 1: add as NOT VALID — only takes a brief lock, does not scan existing rows.
-- New/updated rows are enforced immediately.
ALTER TABLE orders
  ADD CONSTRAINT orders_total_nonneg CHECK (total_cents >= 0) NOT VALID;

-- Step 2: validate existing rows with a weaker lock (SHARE UPDATE EXCLUSIVE),
-- which does not block reads or writes.
ALTER TABLE orders VALIDATE CONSTRAINT orders_total_nonneg;
```

Same pattern for foreign keys:
```sql
ALTER TABLE order_items
  ADD CONSTRAINT order_items_order_fk
  FOREIGN KEY (order_id) REFERENCES orders (id) NOT VALID;
ALTER TABLE order_items VALIDATE CONSTRAINT order_items_order_fk;
```

For a `NOT NULL` on a big table, prefer a `CHECK (col IS NOT NULL) NOT VALID` → `VALIDATE`, then (PG 12+) `SET NOT NULL` can use that validated check to skip the full scan.

### 2.5 Backfill in batches

Never `UPDATE huge_table SET ...` in one statement — it locks every touched row, bloats WAL, and can run for hours. Batch by primary key and commit between batches.

```sql
-- Run repeatedly (loop in your migration runner) until 0 rows affected.
WITH batch AS (
  SELECT id FROM orders
  WHERE currency IS NULL
  ORDER BY id
  LIMIT 5000
)
UPDATE orders o
SET currency = 'USD'
FROM batch
WHERE o.id = batch.id;
```

Each batch is its own transaction. Add a short pause between batches on a busy system to let autovacuum keep up.

### 2.6 Expand / contract pattern

Roll out breaking changes (rename, retype, split) in three deploys so old and new code coexist:

1. **Expand** — add the new column/table. App writes to *both* old and new. Backfill old data in batches (2.5).
2. **Migrate reads** — deploy app version that reads from the new shape; both still written.
3. **Contract** — once nothing reads the old column, drop it.

```sql
-- EXPAND: add new column, backfill, app dual-writes
ALTER TABLE users ADD COLUMN email_normalized text;
-- (batched backfill of email_normalized = lower(email))

-- CONTRACT (a later deploy, after all code uses email_normalized)
ALTER TABLE users DROP COLUMN email;
```

A rename is just expand/contract: never do a bare `ALTER ... RENAME COLUMN` while old code is live — it breaks the old code instantly.

---

## SCOPE 3 — RLS (ROW LEVEL SECURITY)

On Supabase, the `anon` and `authenticated` roles reach the database directly via PostgREST, so **RLS is the only thing standing between a user and every row**. Enable it on every table in an exposed schema.

### 3.1 Enable RLS

```sql
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
```

With RLS enabled and no policies, the table denies all access by default (table owner / `service_role` bypasses RLS). Add explicit policies per operation.

### 3.2 Policy patterns with auth.uid()

`auth.uid()` returns the current user's UUID from their JWT. A "users see only their own rows" set of policies:

```sql
-- SELECT: read own rows
CREATE POLICY "select own profile"
ON public.profiles
FOR SELECT
TO authenticated
USING ( (select auth.uid()) = user_id );

-- INSERT: can only create rows owned by self (WITH CHECK validates the NEW row)
CREATE POLICY "insert own profile"
ON public.profiles
FOR INSERT
TO authenticated
WITH CHECK ( (select auth.uid()) = user_id );

-- UPDATE: USING gates which rows are visible to update;
-- WITH CHECK gates what they may be changed to (prevents reassigning ownership)
CREATE POLICY "update own profile"
ON public.profiles
FOR UPDATE
TO authenticated
USING ( (select auth.uid()) = user_id )
WITH CHECK ( (select auth.uid()) = user_id );

-- DELETE: remove only own rows
CREATE POLICY "delete own profile"
ON public.profiles
FOR DELETE
TO authenticated
USING ( (select auth.uid()) = user_id );
```

Key rules:
- `USING` applies to existing rows (SELECT/UPDATE/DELETE visibility). `WITH CHECK` applies to the resulting row (INSERT/UPDATE). UPDATE uses both.
- Write **separate policies per operation** rather than one `FOR ALL`; it's clearer and easier to audit.

### 3.3 Security definer functions for cross-table checks

When a policy needs to look at another table (e.g. team membership), a self-referential subquery in the policy can recurse or be slow. Move the lookup into a `SECURITY DEFINER` function that bypasses RLS on the lookup table.

```sql
CREATE OR REPLACE FUNCTION private.is_team_member(target_team uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''                         -- prevent search_path hijacking
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.team_members tm
    WHERE tm.team_id = target_team
      AND tm.user_id = (select auth.uid())
  );
$$;

CREATE POLICY "team members read projects"
ON public.projects
FOR SELECT
TO authenticated
USING ( private.is_team_member(team_id) );
```

`SECURITY DEFINER` runs with the function owner's rights, so always pin `SET search_path = ''` and keep the function in a private (non-API-exposed) schema.

### 3.4 RLS performance (these matter a lot at scale)

1. **Wrap auth functions in a subquery.** `(select auth.uid())` instead of bare `auth.uid()` lets Postgres evaluate it once per statement (`InitPlan`) instead of once per row — Supabase benchmarks show this can improve a query by ~95%.
   ```sql
   -- slow: evaluated per row
   USING ( auth.uid() = user_id )
   -- fast: evaluated once
   USING ( (select auth.uid()) = user_id )
   ```

2. **Always specify `TO authenticated` / `TO anon`.** Without it, the policy is also evaluated for roles that can never match, wasting work. Adding the role restriction avoids running the policy for the wrong role entirely.

3. **Index the columns used in policies.** A policy like `(select auth.uid()) = user_id` filters every query on the table by `user_id`, so it must be indexed:
   ```sql
   CREATE INDEX idx_profiles_user_id ON public.profiles USING btree (user_id);
   ```

4. **Filter into a set instead of joining in the policy.** Prefer `team_id IN (select team_id from team_members where user_id = (select auth.uid()))` over a join that fans out rows.

### 3.5 Verify policies

Test as a real role, not as the owner (the owner bypasses RLS):

```sql
-- Simulate an authenticated user
SET request.jwt.claims = '{"sub":"<a-user-uuid>","role":"authenticated"}';
SET ROLE authenticated;
SELECT * FROM public.profiles;       -- should return only that user's rows
RESET ROLE;
```

Also confirm `anon` sees nothing it shouldn't, and run `EXPLAIN ANALYZE` on a policied query to confirm `auth.uid()` appears in an `InitPlan` (evaluated once) and that the policy column uses an index.

---

## Quick checklist

- [ ] Ran `EXPLAIN (ANALYZE, BUFFERS)` before and after the change.
- [ ] Index matches the query's filter + sort order; no redundant/unused indexes added.
- [ ] App traffic goes through the pooler; serverless on transaction mode (6543) with prepared statements off.
- [ ] Deep pagination uses keyset, not OFFSET.
- [ ] Migrations: `lock_timeout` set; `CREATE INDEX CONCURRENTLY`; constraints `NOT VALID` then `VALIDATE`; backfills batched; breaking changes via expand/contract.
- [ ] RLS enabled on every exposed table; per-operation policies; `auth.uid()` wrapped in `(select ...)`; `TO authenticated`/`TO anon` set; policy columns indexed; verified by impersonating the role.
