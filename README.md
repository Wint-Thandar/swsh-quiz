# Somewhere Somehow Quiz App

An interactive quiz application for fans of the Somewhere Somehow GL series.

## Features

- Multiple quiz categories
- Encrypted questions and answers
- User score tracking and leaderboard
- Admin panel for question management
- Responsive design with modern UI
- Performance optimized and refactored codebase

## Security Features

- Encrypted database with Fernet encryption
- Environment variables for sensitive data
- Secure admin authentication
- Protection against timing attacks

## Setup

### Local Development

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables by copying the example file:
   ```
   cp .env.example .env
   ```
4. Edit the `.env` file with your secure passwords
5. Run the application:
   ```
   streamlit run app.py
   ```

### Deployment to Streamlit Cloud

1. **Push your code to GitHub** (make sure `.env` is in `.gitignore` - it should not be committed)

2. **Go to [Streamlit Cloud](https://share.streamlit.io/)** and connect your GitHub repository

3. **Configure Secrets in Streamlit Cloud:**
   - In your Streamlit Cloud app dashboard, go to "Settings" → "Secrets"
   - Add the following secrets (replace with your secure values):
   
   ```toml
   # Streamlit Cloud Secrets (TOML format)
   QUIZ_PASSWORD = "your_secure_quiz_password_here"
   ADMIN_PASSWORD = "your_secure_admin_password_here"
   ENVIRONMENT = "production"
   ```

4. **Deploy the app** - Streamlit Cloud will automatically deploy your app

**Important Security Notes for Deployment:**
- Never commit your `.env` file to GitHub
- Use strong, unique passwords for production
- Environment variables for passwords are required and must be set before deployment

## Environment Variables

The following environment variables should be set in the `.env` file:

- `QUIZ_PASSWORD`: Master password for encrypting quiz data
- `ADMIN_PASSWORD`: Password for accessing the admin panel
- `ENVIRONMENT`: Set to "development" or "production"

## Technical Highlights

- Modular function design with reusable components
- Efficient CSS with consolidated responsive breakpoints
- Clean separation of concerns between UI and logic
- Type hints for better code documentation

## Security Notes

- The `.env` file and database files are excluded from git via `.gitignore`
- Encryption keys are generated from passwords using PBKDF2
- Admin passwords are compared using constant-time comparison to prevent timing attacks