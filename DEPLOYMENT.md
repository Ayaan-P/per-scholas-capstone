# Deployment Guide

This guide explains how to deploy the PerScholas Fundraising Demo to Netlify (frontend) and Render (backend).

## Frontend Deployment (Netlify)

The frontend is automatically deployed via Netlify when you push to the `main` branch.

### Configuration
- **Repository**: Connected to GitHub
- **Branch**: `main`
- **Build Command**: `npm install && npm run build` (configured in `netlify.toml`)
- **Publish Directory**: `frontend/out/`
- **Next.js Mode**: Static Export (`output: 'export'` in `next.config.js`)

The `netlify.toml` file contains the build configuration:
```toml
[build]
base = "frontend"
command = "npm install && npm run build"
publish = "out"
```

---

## Backend Deployment (Render)

The backend requires manual environment variable configuration in Render.

### Step 1: Connect Repository to Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Select your GitHub repository
4. Configure the service:
   - **Name**: `perscholas-fundraising-backend`
   - **Root Directory**: `backend`
   - **Runtime**: `Docker`
   - **Plan**: Standard (or higher if needed)

### Step 2: Set Environment Variables

Go to the service settings and add the following environment variables:

#### Required: Supabase Configuration
```
SUPABASE_URL=https://zjqwpvdcpzeguhdwrskr.supabase.co
SUPABASE_KEY=<your-anon-key-here>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key-here>
```

Get these from your Supabase project:
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to **Settings** → **API**
4. Copy the `Project URL` for `SUPABASE_URL`
5. Copy the `anon public` key for `SUPABASE_KEY`
6. Copy the `service_role secret` key for `SUPABASE_SERVICE_ROLE_KEY`

#### Required: Stripe Configuration
```
STRIPE_SECRET_KEY=<your-stripe-secret-key>
STRIPE_PUBLIC_KEY=<your-stripe-public-key>
STRIPE_WEBHOOK_SECRET=<your-stripe-webhook-secret>
STRIPE_PRICE_PRO=<price-id-for-pro-tier>
STRIPE_PRICE_10_CREDITS=<price-id-for-10-credits>
STRIPE_PRICE_20_CREDITS=<price-id-for-20-credits>
STRIPE_PRICE_100_CREDITS=<price-id-for-100-credits>
```

Get these from your Stripe account:
1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Go to **Developers** → **API Keys**
3. Copy your Secret Key for `STRIPE_SECRET_KEY`
4. Copy your Publishable Key for `STRIPE_PUBLIC_KEY`
5. For webhook secret, go to **Webhooks** and copy the signing secret
6. For Price IDs, go to **Products** and copy the Price IDs you created

#### Required: API Keys
```
GEMINI_API_KEY=<your-gemini-api-key>
ANTHROPIC_API_KEY=<your-anthropic-api-key>
SAM_GOV_API_KEY=<your-sam-gov-api-key>
```

#### Optional: Claude Code Integration
```
CLAUDE_ACCESS_TOKEN=<your-claude-access-token>
CLAUDE_USER_ID=<your-claude-user-id>
```

#### Server Configuration (Usually Pre-set)
```
PORT=8000
FASTAPI_ENV=production
DEBUG=false
```

### Step 3: Deploy

1. Click **"Create Web Service"** to trigger the first deployment
2. Render will automatically build and deploy the backend using the Dockerfile
3. Your backend will be available at: `https://perscholas-fundraising-backend.onrender.com`

### Step 4: Verify Deployment

Test the backend is running:
```bash
curl https://perscholas-fundraising-backend.onrender.com/docs
```

You should see the FastAPI Swagger documentation page.

---

## Environment Variables Summary

### .env File Structure

The backend uses a `.env` file for local development. Create one based on `.env.example`:

```bash
cp backend/.env.example backend/.env
```

Then fill in the values with your actual API keys and service credentials.

**Important**: Never commit the `.env` file to version control. It should be in `.gitignore`.

### Loading Environment Variables

- **Local Development**: `python-dotenv` loads variables from `.env`
- **Render Deployment**: Environment variables are set in the Render dashboard (not from `.env` file)
- **Docker/Container**: Environment variables are passed when the container starts

---

## Troubleshooting

### Backend Deployment Fails with "supabase_key is required"

**Cause**: Render environment variables are not set or are empty.

**Solution**:
1. Go to Render dashboard
2. Click on your backend service
3. Go to **Environment** tab
4. Verify `SUPABASE_URL`, `SUPABASE_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` are set
5. Click **Save**
6. Redeploy the service (go to **Deployments** tab and click redeploy)

### Backend Deployment Fails with Stripe Errors

**Cause**: Stripe environment variables are missing or incorrect.

**Solution**:
1. Verify `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are set in Render
2. Get the correct values from [Stripe Dashboard](https://dashboard.stripe.com)
3. Update the environment variables in Render
4. Redeploy

### Frontend Build Fails on Netlify

**Cause**: Usually related to Next.js configuration or missing dependencies.

**Solution**:
1. Check the Netlify build logs
2. Ensure `netlify.toml` is configured correctly
3. Verify `next.config.js` uses `output: 'export'` for static export
4. Wrap dynamic content in Suspense boundaries

---

## Monitoring

### Frontend Monitoring (Netlify)
- View deployment logs: Netlify Dashboard → Deploys → View logs
- Production URL: Your custom domain configured in Netlify

### Backend Monitoring (Render)
- View logs: Render Dashboard → Service → Logs tab
- View deployments: Render Dashboard → Service → Deployments tab
- Monitor metrics: Render Dashboard → Service → Metrics tab

---

## Security Best Practices

1. **Never commit `.env` files** - They contain sensitive API keys
2. **Use Render's Environment Variables** - Store secrets in Render dashboard, not in code
3. **Rotate API Keys Regularly** - Update Stripe, Supabase, and other API keys periodically
4. **Use Service Role Keys Carefully** - The service role key bypasses Row Level Security (RLS) in Supabase
5. **Monitor Webhook Secrets** - Use Render's webhook signing to verify webhook authenticity

---

## Useful Links

- [Render Documentation](https://render.com/docs)
- [Netlify Documentation](https://docs.netlify.com/)
- [Next.js Static Export](https://nextjs.org/docs/app/building-your-application/deploying/static-exports)
- [Supabase Documentation](https://supabase.com/docs)
- [Stripe API Documentation](https://stripe.com/docs/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
