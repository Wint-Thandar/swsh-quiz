# Deployment Guide for Streamlit Cloud

This guide will help you securely deploy the Somewhere Somehow Quiz App to Streamlit Cloud.

## Pre-Deployment Checklist

### 1. Security Review
- [ ] Verify `.env` file is listed in `.gitignore`
- [ ] Ensure no sensitive data is committed to your repository
- [ ] Generate strong, unique passwords for production
- [ ] Ensure all required environment variables are properly set

### 2. Code Preparation
- [ ] Test the app locally with your production environment variables
- [ ] Commit and push your code to GitHub (excluding `.env`)
- [ ] Verify the repository is accessible

## Deployment Steps

### Step 1: Access Streamlit Cloud
1. Go to [https://share.streamlit.io/](https://share.streamlit.io/)
2. Sign in with your GitHub account
3. Click "New app"

### Step 2: Connect Repository
1. Select your GitHub repository
2. Choose the branch (usually `main` or `master`)
3. Set the main file path to `app.py`
4. Click "Deploy!"

### Step 3: Configure Secrets
1. Once the app is deployed, go to your app's dashboard
2. Click on "Settings" in the sidebar
3. Click on "Secrets"
4. Add the following secrets in TOML format:

```toml
# Production Environment Variables
QUIZ_PASSWORD = "your_very_secure_quiz_password_here"
ADMIN_PASSWORD = "your_very_secure_admin_password_here"
ENVIRONMENT = "production"
```

### Step 4: Verify Deployment
1. Wait for the app to restart (this happens automatically after adding secrets)
2. Test the quiz functionality
3. Test the admin panel with your admin password
4. Verify that encryption is working properly

## Security Best Practices

### Password Requirements
- **Minimum 12 characters**
- **Mix of uppercase, lowercase, numbers, and symbols**
- **Unique passwords** (don't reuse from other services)
- **No dictionary words or personal information**

### Example Strong Passwords
```
QUIZ_PASSWORD = "Kx9#mP2$vL8@nQ5!"
ADMIN_PASSWORD = "Ry4&bN7*wE3%tU9^"
```

### Environment Variables Access
In your Streamlit Cloud app, environment variables are accessed using:
```python
import os
password = os.environ.get('QUIZ_PASSWORD')
```

## Troubleshooting

### Common Issues

1. **App won't start after deployment**
   - Check the logs in Streamlit Cloud dashboard
   - Verify all required secrets are set
   - Ensure `requirements.txt` includes all dependencies

2. **Encryption errors**
   - Verify `QUIZ_PASSWORD` is set correctly
   - Check that the password doesn't contain special characters that might cause issues

3. **Admin access denied**
   - Verify `ADMIN_PASSWORD` is set correctly in secrets
   - Ensure there are no extra spaces in the password

4. **Database issues**
   - The SQLite database will be created automatically on first run
   - Database files are ephemeral in Streamlit Cloud (reset on each deployment)

### Getting Help
- Check Streamlit Cloud documentation: [https://docs.streamlit.io/streamlit-cloud](https://docs.streamlit.io/streamlit-cloud)
- Review app logs in the Streamlit Cloud dashboard
- Ensure your GitHub repository is public or you have the appropriate Streamlit Cloud plan for private repos

## Post-Deployment

### Monitoring
- Monitor app performance in Streamlit Cloud dashboard
- Check for any error logs regularly
- Test admin functionality periodically

### Updates
- Push code changes to GitHub to trigger automatic redeployment
- Update secrets in Streamlit Cloud if passwords need to be changed
- Test thoroughly after any updates

## Security Notes

⚠️ **Important**: 
- Never share your admin password publicly
- Regularly rotate passwords for better security
- Monitor access logs if available
- The database is ephemeral in Streamlit Cloud - data will be lost on redeployment
- Consider implementing additional security measures for production use