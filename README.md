# Authentication & authorization backend

This repository is a small Django API that demonstrates a **custom authentication flow** and a **custom resource access model**. The goal is to show how users are identified after login, how permissions are stored in the database, and how the API responds with the right HTTP status when access should be allowed or denied.

The assignment asked for something beyond “only what the framework gives you out of the box.” Here, **login and profile handling** use Django’s session machinery for convenience, but **who may call which endpoint** is decided by **your own tables and checks**, not by Django’s built-in admin permissions alone.

---

## What you get in one glance

| Area | What it does |
|------|----------------|
| **Users** | Register with email/password, log in/out, read and update profile, soft-delete account |
| **Authorization** | Roles, resources, actions, and explicit allow rules in PostgreSQL (or SQLite locally) |
| **Administration** | JSON API for users with the **Administrator** role to list and change access rules |
| **Demo “business”** | Two read-only mock endpoints that succeed or fail based on those rules |
| **HTTP behavior** | `401` when the caller is not a valid logged-in active user; `403` when they are, but the rule set says no |

### First visit in a browser (not an error)

Opening **`http://127.0.0.1:8000/`** returns **`200`** with a short JSON message explaining that this is an API and pointing to **`/api/`**. Same idea for **`/api/`**: a small index of main routes. That way a reviewer who pastes the base URL into a browser sees something **intentional**, not a blank page or a confusing protocol error.

All real operations still use the JSON endpoints under **`/api/...`** (Postman, curl, or another HTTP client).

---

## Why the access model looks like this

Many systems separate **authentication** (“who is this?”) from **authorization** (“what may they do?”). This project does the same.

**Authentication** after login is tied to the **session cookie**: the server remembers the user for subsequent requests in the same client (e.g. Postman with cookies enabled, or a browser).

**Authorization** is **data-driven**. A user can have one or more **roles**. Each role has **permission rules**: for a given **resource** (e.g. “projects”) and **action** (e.g. “read”), the rule says whether access is **allowed**. At request time, the code loads the user’s roles and checks whether **any** role has an **allowing** rule for that resource and action.

That design is easy to explain to a client, easy to inspect in the database, and matches the test task: *rules in tables + API to maintain them + mock resources that obey those rules*.

---

## Database schema (authorization-related)

Django creates table names from the app label and model name. The important ones for this demo:

- **`accounts_user`** — Custom user: email as login, profile names, `is_active` (used for soft delete), password hash, staff flags for Django admin if you use it.
- **`accounts_role`** — Named roles (e.g. Administrator, Manager, Viewer).
- **`accounts_resource`** — Named things you protect (e.g. `projects`, `reports`, `access_rules`).
- **`accounts_action`** — Verbs (e.g. `read`, `update`).
- **`accounts_permissionrule`** — One row per *(role, resource, action)* with `is_allowed`. This is the core matrix.
- **`accounts_userrole`** — Links users to roles.

**Soft delete:** `DELETE /api/users/me/delete` sets `is_active` to `false`, clears the session, and blocks future logins. The row stays in `accounts_user` for audit or recovery workflows.

**Passwords** are stored only as **Django hashes** (never plain text). Demo accounts are created or refreshed by the `seed_data` command so reviewers always have working credentials on a clean database.

---

## How a request is allowed or rejected

When a protected view runs:

1. If there is **no authenticated user**, or the user is **inactive** → response **`401`** with a short JSON message (authentication required / deactivated).
2. If the user **is** authenticated and active, the code looks up their **roles** and then **`PermissionRule`** rows for the required **resource** and **action**.
3. If **no** matching **allowed** rule exists → **`403`** (access denied).
4. If at least one **allowed** rule exists → the view runs normally (**`200`**, etc.).

This matches the specification: unverified caller → `401`; verified but not permitted → `403`.

---

## API reference

Base path: **`http://127.0.0.1:8000/api`** (adjust host/port if needed).

Use **`Content-Type: application/json`** on requests with a body. For session login, the client must **store and send cookies** on follow-up requests (Postman: cookies enabled).

### User lifecycle

| Method | Path | Purpose |
|--------|------|--------|
| `POST` | `/api/auth/register` | Create account. Body: `email`, `password`, `password_confirm`, `first_name`; optional `last_name`, `middle_name`. |
| `POST` | `/api/auth/login` | Body: `email`, `password`. Establishes session. |
| `POST` | `/api/auth/logout` | Ends session. Requires login. |
| `GET` | `/api/users/me` | Current user profile. Requires login. |
| `PATCH` | `/api/users/me` | Update `first_name`, `last_name`, `middle_name`. Requires login. |
| `DELETE` | `/api/users/me/delete` | Soft delete + logout. Requires login. |

### Mock business resources (permission checks)

| Method | Path | Required permission (conceptually) |
|--------|------|-----------------------------------|
| `GET` | `/api/business/projects` | Role must allow **read** on resource **`projects`**. |
| `GET` | `/api/business/reports` | Role must allow **read** on resource **`reports`**. |

Responses are simple static JSON lists—enough to prove the access layer, without building real domain tables.

### Access rule administration (Administrator role)

These require permission on resource **`access_rules`** (see seeded rules): **read** for listing, **update** for changes.

| Method | Path | Purpose |
|--------|------|--------|
| `GET` | `/api/admin/permissions` | List all permission rules. |
| `POST` | `/api/admin/permissions/create` | Create or update a rule. Body: `role`, `resource`, `action`, `is_allowed` (optional, default true). |
| `DELETE` | `/api/admin/permissions/<rule_id>` | Remove a rule by id. |
| `POST` | `/api/admin/users/<user_id>/roles` | Assign a role to a user. Body: `role` (role name). |

---

## Running the project

### Option A — Local Python (SQLite by default)

From the project root:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

SQLite file: `db.sqlite3` in the project root (created automatically).

### Option B — Docker (PostgreSQL)

```bash
docker compose up --build
```

The `web` container runs migrations and `seed_data` on startup, then serves on port **8000**. Postgres credentials match `docker-compose.yml` (`auth_system` database, user `auth_user`).

**Important:** If you inspect data in pgAdmin, connect to **this** Postgres instance. If you run `manage.py` on the host **without** database environment variables, Django uses **SQLite**—that is a different database than Docker Postgres.

---

## Seeded accounts (for reviewers)

After `seed_data`:

| Email | Password | Role (via `UserRole`) |
|-------|----------|------------------------|
| `admin@test.local` | `Admin12345!` | Administrator |
| `manager@test.local` | `Manager12345!` | Manager |
| `viewer@test.local` | `Viewer12345!` | Viewer |

You can register additional users via **`POST /api/auth/register`**. New users have **no roles** until an administrator assigns one (e.g. via **`POST /api/admin/users/<id>/roles`**) or you adjust data in the shell.

---

## Suggested review scenario (manual)

A concise path a client can follow in Postman:

1. **Without logging in**, call `GET /api/business/projects` → expect **`401`**.
2. Log in as **`viewer@test.local`** → `GET /api/business/projects` → **`200`**; `GET /api/business/reports` → **`403`** (default seed rules).
3. Log in as **`admin@test.local`**, `POST /api/admin/permissions/create` to allow Viewer **read** on **reports** → log in again as viewer → `GET /api/business/reports` → **`200`**.
4. Register a user, log in, call **`DELETE /api/users/me/delete`**, then try to log in again → **`401`**.

---

## Automated tests

```bash
python manage.py test
```

Tests cover representative cases (login, permission denial, soft-delete login block, non-admin denied from rule API).

---

## Implementation notes (for technical readers)

- API views that accept JSON bodies are marked **CSRF-exempt** so tools like Postman can call them without a browser CSRF token. For a production browser-only SPA you would typically switch to token/JWT auth or a proper CSRF strategy instead.
- Django’s **`/admin/`** site is optional: it uses `is_staff` / `is_superuser`. Your **JSON “Administrator”** capabilities for `/api/admin/...` come from the **custom role and permission rules**, not automatically from `is_superuser`.

---

## Repository layout (high level)

- `auth_system/` — Django project settings and root URLs.
- `accounts/` — Custom user model, access-control models, API views, permissions helpers, URL include under `/api/`.
- `accounts/management/commands/seed_data.py` — Demo data and password reset for the three seed users.
- `Dockerfile`, `docker-compose.yml` — Optional containerized run with PostgreSQL.

If anything in this README does not match behavior you see, check **which database** the running server uses (SQLite vs Postgres) and re-run **`seed_data`** against that same environment.
