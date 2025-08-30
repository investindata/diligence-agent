# Google OAuth2 Setup Instructions

This guide will help you set up authenticated access to Google Drive and Google Docs for the Diligence Agent.

## Overview

After setup, you'll be able to:
- ✅ Access private Google Docs that you own
- ✅ Access Google Docs shared with your account
- ✅ No longer need documents to be "Anyone with the link"
- ✅ One-time setup, then automatic authentication

## Step 1: Install New Dependencies

First, install the new Google API dependencies:

```bash
# From your project root directory:
cd /Users/gbezerra/Dev/projects/iid-diligence-agent/diligence_agent
uv sync
# or
crewai install
```

## Step 2: Google Cloud Console Setup

### 2.1 Create/Select Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Gmail account
3. Either:
   - **Create new project**: Click "New Project" → Enter name (e.g., "Diligence Agent") → Create
   - **Select existing project**: Click the project dropdown at the top

### 2.2 Enable Required APIs

1. In the left sidebar, go to **APIs & Services** → **Library**
2. Search for and enable these APIs:
   - **Google Drive API** → Click "Enable"
   - **Google Docs API** → Click "Enable"
   - **Google Sheets API** → Click "Enable" (optional, for spreadsheets)

### 2.3 Create OAuth2 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** → **OAuth client ID**
3. If prompted to configure consent screen:
   - Choose **External** (unless you have Google Workspace)
   - Fill in required fields:
     - **App name**: "Diligence Agent" (or your choice)
     - **User support email**: Your email
     - **Developer contact**: Your email
   - Click **Save and Continue** through all screens
4. Back to **Create OAuth client ID**:
   - **Application type**: Choose **Desktop application**
   - **Name**: "Diligence Agent Desktop" (or your choice)
   - Click **Create**
5. **Important**: Copy the credentials:
   - **Client ID**: Something like `123456789-abc...apps.googleusercontent.com`
   - **Client Secret**: Something like `GOCSPX-abc123...`

## Step 3: Add Credentials to .env File

Open your `.env` file and fill in the credentials:

```bash
# Your existing variables...
OPENAI_API_KEY=...
SERPER_API_KEY=...

# Add these new lines with your credentials:
GOOGLE_CLIENT_ID=123456789-abc...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123...
GOOGLE_REFRESH_TOKEN=
# ☝️ Leave GOOGLE_REFRESH_TOKEN empty for now - the setup script will fill this
```

## Step 4: Run the OAuth2 Setup Script

Now run the one-time authentication setup:

```bash
cd /Users/gbezerra/Dev/projects/iid-diligence-agent/diligence_agent
python setup_google_auth.py
```

### What happens:
1. Script checks your `.env` credentials
2. Opens your browser automatically
3. Google login page appears
4. You log in with your Gmail account
5. Google asks: "Diligence Agent wants to access your Google Drive" → Click **Allow**
6. Browser shows "Authentication successful"
7. Script saves refresh token to `.env` file
8. Done! ✅

## Step 5: Test the Integration

Test with a private document:

1. Create or find a Google Doc in your account
2. Make it **private** (not "Anyone with the link")
3. Copy the URL
4. Test the GoogleDocProcessor tool in your application

## Troubleshooting

### "Error: Google OAuth2 credentials not configured!"
- Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are filled in `.env`
- Make sure there are no extra spaces

### "Access denied - document is not shared with your Google account"
- The document isn't accessible to your Gmail account
- Either share the document with yourself, or make it "Anyone with the link" temporarily

### "Authentication failed" during setup
1. Check that Google Drive API and Google Docs API are enabled
2. Make sure OAuth consent screen is configured
3. Verify Client ID and Client Secret are correct
4. Try creating new OAuth2 credentials

### "No refresh token received"
- You might have existing permissions for this app
- Go to [Google Account Settings](https://myaccount.google.com/permissions)
- Remove "Diligence Agent" from connected apps
- Run setup script again

## How It Works

### Authentication Flow:
```
1. Application loads GOOGLE_REFRESH_TOKEN from .env
2. Uses refresh token to get short-lived access token
3. Makes authenticated API calls to Google Drive/Docs
4. If auth fails, falls back to public access (original behavior)
```

### Fallback Behavior:
- If OAuth2 credentials are missing/invalid → Uses public access
- If document is inaccessible → Tries public export URLs
- Your existing public documents will continue to work

## Security Notes

- ✅ **Refresh tokens** are stored (safe, can be revoked)
- ✅ **No passwords** are stored anywhere
- ✅ **Limited scope** (only Google Drive read access)
- ✅ **.env file** is not committed to git
- ✅ **Industry standard** OAuth2 flow

## Revoking Access

To revoke access later:
1. Go to [Google Account Settings](https://myaccount.google.com/permissions)
2. Find "Diligence Agent" → Remove access
3. Delete `GOOGLE_REFRESH_TOKEN` from `.env`
4. Application will fall back to public access only

## Success Indicators

After successful setup:
- ✅ Your `.env` file has a long `GOOGLE_REFRESH_TOKEN` value
- ✅ The setup script shows "Setup complete!"
- ✅ Private documents work in your application
- ✅ GoogleDocProcessor logs show "✅ Successfully accessed document via Google Docs API"

## Team Development

### For New Developers:

Each developer needs to run the setup process individually:

1. **Get Google Cloud credentials** (two options):
   - **Option A**: Create your own Google Cloud project (recommended)
   - **Option B**: Get shared Client ID/Secret from team lead

2. **Run setup on your machine**:
   ```bash
   # Add credentials to your local .env file
   GOOGLE_CLIENT_ID=your_or_shared_client_id
   GOOGLE_CLIENT_SECRET=your_or_shared_client_secret
   
   # Run setup script with YOUR Google account
   python setup_google_auth.py
   ```

3. **Test your setup**:
   ```bash
   python test_google_auth.py
   ```

### Important Notes:

- ❌ **Never commit `.env` files** - they contain personal refresh tokens
- ❌ **Never share refresh tokens** - they're tied to individual Google accounts
- ✅ **Each developer uses their own Google account** for authentication
- ✅ **Documents must be shared** with each developer's Google account
- ✅ **Test script helps verify** individual setup is working

### Document Access:

For team members to access the same private documents:
1. Share documents with each team member's Google account, OR
2. Use a shared Google account for document ownership (less secure)