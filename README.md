# NutriAI — Intelligent Nutrition

NutriAI helps users explore meal nutrition, track daily intake, and build healthier routines.

## Run locally

```sh
npm install
npm run dev
```

Use `npm run build` to create a production build and `npm run lint` to run the project linter.

## Authentication setup

NutriAI uses Supabase Auth for email/password signup, login, session persistence, password reset requests, and logout. The app only needs the Supabase project URL and its **publishable/anon key** in the browser. Never put a database password, `service_role`, or secret key in a `VITE_` variable.

1. Create a Supabase project.
2. In **Project Settings → API**, copy the Project URL and the publishable key (or legacy anon public key).
3. Copy `.env.example` to `.env.local` and fill in:

   ```env
   VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
   VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY
   ```

4. In the Supabase SQL Editor, run [`supabase/migrations/20261029000000_create_profiles.sql`](./supabase/migrations/20261029000000_create_profiles.sql). It creates `public.profiles`, enables RLS, restricts profile reads/updates to the signed-in owner, and adds a database trigger that copies `full_name` from signup metadata. The browser client cannot insert profiles directly.
5. In **Authentication → Providers**, enable Email. Configure email confirmation as desired. With confirmation required, a successful signup displays a confirmation message and the user can log in after confirming; access is granted only after Supabase returns a session.
6. In **Authentication → URL Configuration**, set the Site URL to your app origin and add local/deployed origins to the allowed redirect URLs (for example `http://localhost:5173/**` and `http://127.0.0.1:5173/**` for local development).
7. Restart the Vite server after setting environment variables: `npm run dev`.

The Supabase client persists and refreshes its auth session; passwords are sent to Supabase Auth and are never saved by this app. Signup stores the full name in Supabase Auth user metadata and the database trigger creates the corresponding profile row. Demo mode is development-only; production routes require a real Supabase session. Keep `.env.local` private; it is ignored by git.
