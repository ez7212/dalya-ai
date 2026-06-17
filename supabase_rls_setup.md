# Supabase RLS Setup

Run this in Supabase Dashboard → SQL Editor → New Query.

## Step 1 — Enable RLS on all tables

```sql
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE buyer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_inquiries ENABLE ROW LEVEL SECURITY;
```

## Step 2 — Allow full access for the service role

```sql
CREATE POLICY "service_full_access" ON listings FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_full_access" ON conversations FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_full_access" ON messages FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_full_access" ON buyer_profiles FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_full_access" ON listing_inquiries FOR ALL TO service_role USING (true) WITH CHECK (true);
```

## Step 3 — Update your connection string

In Supabase: **Project Settings → API → service_role** (secret key).

Update `.env`:

```
DATABASE_URL=postgresql://postgres.[project-ref]:[service-role-key]@aws-0-[region].pooler.supabase.com:6543/postgres
```
