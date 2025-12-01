# Production API Debugging Guide

## Problem Summary

The SerpAPI and OpenAI APIs are not working correctly in production, likely returning mock data instead of real results.

## Root Causes Identified

### 1. **Missing Environment Variables in Production**
   - The `render.yaml` file doesn't include environment variable definitions
   - API keys need to be set in the Render.com dashboard, not in the YAML file
   - Without these keys, the system falls back to mock data

### 2. **Silent Failures**
   - The code was catching errors but not logging them clearly
   - Mock data was being returned without clear warnings
   - Users couldn't tell if they were seeing real or mock data

### 3. **API Key Configuration Issues**
   - Keys might be missing, invalid, or expired
   - Keys might be set in environment but not accessible to Django settings
   - API credits might be exhausted

## Changes Made

### 1. Enhanced Error Logging
   - Added detailed error logging with `[ERROR]` and `[WARNING]` prefixes
   - Added stack traces for debugging
   - Clear messages when API keys are missing
   - Better error messages when API calls fail

### 2. Improved SerpAPI Connector
   - Clear warnings when using mock data
   - Detailed error logging for API failures
   - Better handling of authentication errors (401/403)
   - Logs response bodies for debugging

### 3. Improved OpenAI Service Error Handling
   - Separate handling for missing API key (ValueError)
   - Better error messages to users
   - Full stack traces in logs

### 4. Created Diagnostic Tools
   - `debug_production_apis.py` - Comprehensive API diagnostic script
   - Can be run on production to identify issues

## How to Fix Production Issues

### Step 1: Check Environment Variables in Render.com

1. Go to your Render.com dashboard
2. Navigate to your service (cs4300-groupgo)
3. Go to **Environment** tab
4. Verify these environment variables are set:
   - `SERP_API_KEY` - Your SerpAPI key
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `HOTEL_API_KEY` - Your Makcorps Hotel API key (if using)

### Step 2: Verify API Keys Are Valid

**SerpAPI:**
- Check your dashboard: https://serpapi.com/dashboard
- Verify you have credits remaining (free tier: 100 searches/month)
- Test your key manually if needed

**OpenAI:**
- Check your dashboard: https://platform.openai.com/api-keys
- Verify the key is active and not revoked
- Check usage/credits: https://platform.openai.com/usage

### Step 3: Run Diagnostic Script

On your production server or locally with production settings:

```bash
python debug_production_apis.py
```

This will:
- Check if API keys are configured
- Test SerpAPI flights
- Test SerpAPI activities
- Test OpenAI API
- Test OpenAI consolidation function
- Provide detailed error messages

### Step 4: Check Production Logs

After deploying the improved error logging, check your Render.com logs:

1. Go to your service in Render dashboard
2. Click on **Logs** tab
3. Look for:
   - `[WARNING]` messages about missing API keys
   - `[ERROR]` messages about API failures
   - Stack traces showing where errors occur

### Step 5: Test a Search

1. Log in to https://groupgo.me/
2. Create a test search
3. Check the logs for:
   - `[WARNING] SerpApi API key not configured` - Key missing
   - `[ERROR] SerpApi returned status code 401` - Invalid key
   - `[ERROR] SerpApi returned status code 403` - Forbidden (no credits?)
   - `[ERROR] OpenAI API key not configured` - OpenAI key missing

## Common Issues and Solutions

### Issue: "Using mock flight data"
**Solution:** Set `SERP_API_KEY` environment variable in Render.com

### Issue: "SerpApi returned status code 401"
**Solution:** 
- Verify the API key is correct
- Check if key was regenerated (old key invalid)
- Ensure no extra spaces in the key

### Issue: "SerpApi returned status code 403"
**Solution:**
- Check API credits/quota at https://serpapi.com/dashboard
- Free tier: 100 searches/month
- Upgrade plan if needed

### Issue: "OpenAI API key not configured"
**Solution:** Set `OPENAI_API_KEY` environment variable in Render.com

### Issue: "OpenAI API error: Rate limit exceeded"
**Solution:**
- Check usage at https://platform.openai.com/usage
- Wait for rate limit to reset
- Consider upgrading plan

## Files Modified

1. `ai_implementation/views.py`
   - Enhanced error logging for SerpAPI flights
   - Enhanced error logging for SerpAPI activities
   - Better OpenAI error handling with stack traces

2. `ai_implementation/serpapi_connector.py`
   - Clear warnings when using mock data
   - Detailed error logging for HTTP errors
   - Better authentication error detection

3. `debug_production_apis.py` (NEW)
   - Comprehensive diagnostic tool
   - Tests all APIs
   - Provides actionable recommendations

## Next Steps

1. **Deploy the changes** to production
2. **Set environment variables** in Render.com if not already set
3. **Run the diagnostic script** to verify configuration
4. **Test a search** and check logs
5. **Monitor logs** for any remaining issues

## Testing Locally

To test with production-like settings:

```bash
# Set environment variables
export SERP_API_KEY=your-key-here
export OPENAI_API_KEY=your-key-here

# Run diagnostic
python debug_production_apis.py

# Or test the full flow
python manage.py runserver
# Then test a search in the UI
```

## Additional Notes

- The system gracefully falls back to mock data when APIs fail
- Mock data is clearly marked with `is_mock: True`
- Users will see warnings/errors in the UI when APIs fail
- All errors are logged with full stack traces for debugging


