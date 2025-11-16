# GitHub App Permissions Fix Guide

## Problem
Some private repositories fail to clone with error: `fatal: could not read Username for 'https://github.com'`

This indicates the GitHub App token doesn't have access to those repositories.

## Solution: Update GitHub App Permissions

### Required Permissions for Cloning Repositories

**Repository Permissions:**
- ✅ **Contents**: Read (REQUIRED - this is the ONLY permission needed for cloning)
- ✅ **Metadata**: Read (REQUIRED - for reading repository information)

**Organization Permissions:**
- ✅ **Members**: Read-only (REQUIRED - for accessing private repositories)

**NOT Required:**
- ❌ **Administration**: NOT needed for cloning (only for admin tasks)

### Step-by-Step Fix

1. **Go to GitHub App Settings:**
   - Navigate to: https://github.com/organizations/{your-org}/settings/apps
   - Find your Sparta GitHub App

2. **Update Permissions:**
   - Click on your app → "Permissions & events"
   - Set Repository permissions:
     - Contents: **Read**
     - Metadata: **Read**
   - Set Organization permissions:
     - Members: **Read-only**
   - **Save changes**

3. **Verify Installation:**
   - Go to: "Install App" tab
   - Find your organization installation
   - **CRITICAL**: Must show "All repositories" (not "Only select repositories")
   - If it shows "Only select repositories":
     - Click "Configure"
     - Change to "All repositories"
     - Save

4. **Test:**
   - Run the daily scan workflow
   - Verify all repos (including private ones) clone successfully

## Quick Checklist

- [ ] Contents: Read permission set
- [ ] Metadata: Read permission set
- [ ] Members: Read-only permission set
- [ ] App installed on "All repositories" (not individual repos)
- [ ] Secrets (SPARTA_APP_ID, SPARTA_APP_PRIVATE_KEY) configured
- [ ] Workflow can generate token successfully

## Why This Fixes the Issue

- **Contents: Read** allows the app to clone repository content
- **Members: Read-only** allows the app to access private organization repositories
- **"All repositories"** installation ensures the app has access to all repos, not just selected ones
- **Administration permission is NOT needed** - it's only for managing repository settings
