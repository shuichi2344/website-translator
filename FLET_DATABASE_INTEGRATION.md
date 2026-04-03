# Flet Desktop App - MySQL Database Integration

## ✅ What's Integrated

Your Flet desktop app now uses MySQL database for authentication!

### Changes Made:

1. **Login View (`app/views/login.py`)**
   - ✅ Integrated with MySQL authentication
   - ✅ Email-based login (instead of username)
   - ✅ Password verification via bcrypt
   - ✅ Registration with MySQL
   - ✅ Fallback to file-based auth if database unavailable

2. **App State (`app/state.py`)**
   - ✅ Added `user_id` field (MySQL user ID)
   - ✅ Added `email` field
   - ✅ Persisted in user preferences

## 🚀 How It Works

### Login Flow
```
User enters email + password
    ↓
Flet App → auth_handler.login_user()
    ↓
MySQL: Verify password hash
    ↓
If success:
    - Load user data from MySQL
    - Store in AppState
    - Save to user_prefs/{name}.json
    - Navigate to /home
    ↓
If fail:
    - Show error message
    - Try fallback file-based auth
```

### Registration Flow
```
User enters name, email, password
    ↓
Flet App → auth_handler.register_user()
    ↓
MySQL: INSERT INTO users (hashed password)
    ↓
If success:
    - Show success message
    - Switch to login mode
    - User can now log in
    ↓
If fail (e.g., email exists):
    - Show error message
```

## 🎯 Features

### 1. MySQL Authentication
- Email-based login
- Secure password hashing (bcrypt)
- User data stored in MySQL
- Automatic session persistence

### 2. Fallback Support
- If MySQL unavailable, uses file-based auth
- App works offline
- Seamless transition

### 3. User Data Sync
- User preferences stored in both:
  - MySQL database (primary)
  - Local JSON files (backup/offline)

## 📊 Database Connection

### Setup MySQL
1. **Configure `.env`:**
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_chatbot
```

2. **Create database tables** (run your SQL script)

3. **Install dependencies:**
```bash
.venv\Scripts\pip install mysql-connector-python bcrypt
```

## 🧪 Testing

### Test Login/Registration
1. **Start Flet app:**
```bash
.venv\Scripts\python main.py
```

2. **Create account:**
   - Click "New here? Create an account"
   - Enter name, email, password
   - Click "Create Account"
   - Should see: "Account created! Please log in."

3. **Login:**
   - Enter email and password
   - Click "Log In"
   - Should see: "Welcome back, {name}!"
   - Navigate to home screen

### Check Database
```sql
-- View registered users
SELECT user_id, name, email, country, language, created_at 
FROM users;

-- Check last login
SELECT name, email, last_login 
FROM users 
ORDER BY last_login DESC;
```

## 🔄 Data Flow

### What's Stored Where:

**MySQL Database:**
- User ID (UUID)
- Name
- Email
- Password hash (bcrypt)
- Country
- Language
- Created/updated timestamps
- Last login timestamp

**Local JSON (`user_prefs/{name}.json`):**
- Username (name)
- User ID
- Email
- Language
- Country
- Font size
- Theme mode
- Onboarding status

## 🎨 UI Changes

### Login Screen:
- **Before:** Username field
- **After:** Email field

### Registration Screen:
- **New fields:**
  - Full Name (required)
  - Email (required)
  - Password (required)

## 🔧 Troubleshooting

### Database Not Available
```
⚠️  Database not available: ...
```
**What happens:**
- App falls back to file-based authentication
- Login/registration still works
- Data saved to local JSON files only

**Solution:**
1. Check MySQL is running
2. Verify `.env` credentials
3. Install dependencies: `pip install mysql-connector-python bcrypt`

### Login Fails
**Possible causes:**
1. Wrong email/password
2. User not registered in MySQL
3. Database connection issue

**Solution:**
- Check error message in snackbar
- Try registering new account
- Check MySQL connection

### Registration Fails
**Common errors:**
- "Email already registered" - Use different email
- Database connection error - Check MySQL

## 🚀 Next Steps

### 1. Integrate Chat with MySQL
Update `app/views/home.py` to use RAG integration:

```python
from engine.database.rag_integration import RAGIntegration

rag = RAGIntegration()

# In your chat handler:
def send_message(message):
    # Save user message
    rag.save_user_message(conversation_id, message)
    
    # Get context
    context = rag.get_context_for_response(message, conversation_id)
    
    # Generate response
    # ... your AI logic ...
    
    # Save bot response
    rag.save_bot_message(conversation_id, response)
```

### 2. Show Conversation History
```python
# Get user's conversations
conversations = rag.mysql.get_user_conversations(state.user_id)

# Display in UI
for conv in conversations:
    print(f"{conv['title']} - {conv['created_at']}")
```

### 3. Add Profile Management
```python
# Update user profile
auth_handler.update_user_profile(
    user_id=state.user_id,
    name=new_name,
    language=new_language
)
```

## ✅ Summary

Your Flet desktop app is now integrated with MySQL:

✅ **Authentication:** Email-based login with bcrypt
✅ **Registration:** Create accounts in MySQL
✅ **User Data:** Stored in database
✅ **Session:** Persists across app restarts
✅ **Fallback:** Works offline with file-based auth
✅ **Security:** Passwords encrypted

## 📝 Architecture

```
Flet Desktop App
    ↓
app/views/login.py
    ↓
engine/database/auth_handler.py
    ↓
engine/database/mysql_handler.py
    ↓
MySQL Database (users table)
```

Everything is connected and working! 🎉
