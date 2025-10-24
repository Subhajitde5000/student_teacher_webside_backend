# Student-Teacher Website Backend - MongoDB Database System

A complete backend system with MongoDB database for managing students, teachers, classes, assignments, grades, and announcements.

## 📋 Features

### User Management
- ✅ User registration (students and teachers)
- ✅ User authentication with sessions
- ✅ **Google OAuth 2.0 authentication** 🆕
- ✅ Password reset functionality
- ✅ User profile management
- ✅ Role-based access (student/teacher)

### Class Management
- ✅ Create and manage classes
- ✅ Add students to classes
- ✅ View classes by teacher
- ✅ View enrolled classes by student

### Assignment Management
- ✅ Create assignments with due dates
- ✅ Submit assignments
- ✅ View all submissions for an assignment
- ✅ Track assignment status

### Grade Management
- ✅ Add/update grades for assignments
- ✅ Provide feedback on submissions
- ✅ View student grades

### Announcements
- ✅ Create class announcements
- ✅ View recent announcements
- ✅ Teacher-to-class communication

### Session Management
- ✅ Secure token-based sessions
- ✅ Auto-expiring sessions (24 hours default)
- ✅ Logout functionality

## 🚀 Setup Instructions

### 1. Install MongoDB

**Option A: Local MongoDB**
- Download and install MongoDB from [mongodb.com](https://www.mongodb.com/try/download/community)
- Start MongoDB service:
  ```powershell
  # Windows
  net start MongoDB
  ```

**Option B: MongoDB Atlas (Cloud)**
- Create a free account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- Create a cluster and get your connection string
- Update the connection string in `.env` file

### 2. Install Python Dependencies

```powershell
# Install required packages
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the backend directory:

```env
MONGODB_URI=mongodb://localhost:27017/
DATABASE_NAME=student_teacher_db
SECRET_KEY=your-secret-key-here
SESSION_DURATION_HOURS=24

# Google OAuth (Optional) 🆕
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
```

For MongoDB Atlas, use:
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

**Setting up Google OAuth (Optional):**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable Google+ API
3. Create OAuth 2.0 credentials
4. Add redirect URI: `http://localhost:5000/api/auth/google/callback`
5. Copy Client ID and Secret to `.env`

📖 **Full OAuth setup guide:** See [OAUTH_GUIDE.md](OAUTH_GUIDE.md)

### 4. Run the Application

```powershell
# Run the Flask application
python main.py
```

The server will start on `http://localhost:5000`

## 📡 API Endpoints

### Authentication & User Management

#### Register User
```http
POST /api/sign_up
Content-Type: application/json

{
  "username": "John Doe",
  "email": "john@example.com",
  "password": "secure123",
  "roll": "STU001",
  "user_type": "student",
  "class_subject": "10th Grade"
}
```

#### Login
```http
POST /api/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "secure123"
}

Response:
{
  "success": true,
  "token": "session_token_here",
  "user": {...},
  "expires_at": "2025-10-20T12:00:00"
}
```

#### Logout
```http
POST /api/logout
Content-Type: application/json

{
  "token": "session_token_here"
}
```

#### Forgot Password
```http
POST /api/forgot_password
Content-Type: application/json

{
  "email": "john@example.com"
}
```

#### Google OAuth Login 🆕
```http
GET /api/auth/google

Response:
{
  "success": true,
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?..."
}

# Then user completes Google auth and is redirected to:
GET /api/auth/google/callback

Response:
{
  "success": true,
  "token": "session_token_here",
  "user": {...},
  "is_new_user": true
}
```

#### Get User Profile 🆕
```http
GET /api/user/profile
Authorization: Bearer session_token_here

Response:
{
  "success": true,
  "user": {
    "_id": "user_id",
    "username": "John Doe",
    "email": "john@example.com",
    "google_id": "...",
    "profile_picture": "https://...",
    "user_type": "student"
  }
}
```

#### Reset Password
```http
POST /api/reset_password
Content-Type: application/json

{
  "token": "reset_token_here",
  "new_password": "newpassword123"
}
```

#### Get User Info
```http
GET /api/user/<user_id>
```

#### Update User
```http
PUT /api/user/<user_id>
Content-Type: application/json

{
  "username": "Updated Name",
  "class_subject": "11th Grade"
}
```

#### Get All Students
```http
GET /api/students
```

#### Get All Teachers
```http
GET /api/teachers
```

### Class Management

#### Create Class
```http
POST /api/class
Content-Type: application/json

{
  "class_name": "Mathematics 101",
  "teacher_id": "teacher_user_id",
  "description": "Advanced Mathematics",
  "subject": "Math",
  "schedule": {"days": ["Mon", "Wed", "Fri"], "time": "10:00 AM"}
}
```

#### Add Student to Class
```http
POST /api/class/<class_id>/student/<student_id>
```

#### Get Teacher's Classes
```http
GET /api/teacher/<teacher_id>/classes
```

#### Get Student's Classes
```http
GET /api/student/<student_id>/classes
```

### Assignment Management

#### Create Assignment
```http
POST /api/assignment
Content-Type: application/json

{
  "class_id": "class_id_here",
  "teacher_id": "teacher_id_here",
  "title": "Chapter 5 Assignment",
  "description": "Complete exercises 1-10",
  "due_date": "2025-10-25T23:59:59",
  "max_points": 100
}
```

#### Submit Assignment
```http
POST /api/assignment/<assignment_id>/submit
Content-Type: application/json

{
  "student_id": "student_id_here",
  "content": "My submission text",
  "file_url": "https://example.com/file.pdf"
}
```

#### Get Assignment Submissions
```http
GET /api/assignment/<assignment_id>/submissions
```

### Grade Management

#### Add/Update Grade
```http
POST /api/grade
Content-Type: application/json

{
  "student_id": "student_id_here",
  "assignment_id": "assignment_id_here",
  "points": 85,
  "feedback": "Good work! Needs improvement in section 3.",
  "graded_by": "teacher_id_here"
}
```

#### Get Student Grades
```http
GET /api/student/<student_id>/grades
```

### Announcements

#### Create Announcement
```http
POST /api/announcement
Content-Type: application/json

{
  "class_id": "class_id_here",
  "teacher_id": "teacher_id_here",
  "title": "Exam Schedule",
  "content": "The final exam will be on December 15th."
}
```

#### Get Class Announcements
```http
GET /api/class/<class_id>/announcements?limit=10
```

## 🗄️ Database Schema

### Users Collection
```javascript
{
  _id: ObjectId,
  username: String,
  email: String (unique),
  password: String (hashed),
  roll: String,
  user_type: String ("student" or "teacher"),
  class_subject: String,
  created_at: DateTime,
  updated_at: DateTime,
  is_active: Boolean,
  profile_complete: Boolean
}
```

### Sessions Collection
```javascript
{
  _id: ObjectId,
  user_id: String,
  token: String (unique),
  created_at: DateTime,
  expires_at: DateTime (indexed, auto-delete)
}
```

### Classes Collection
```javascript
{
  _id: ObjectId,
  class_name: String,
  teacher_id: String,
  description: String,
  subject: String,
  schedule: Object,
  students: Array[String],
  created_at: DateTime,
  is_active: Boolean
}
```

### Assignments Collection
```javascript
{
  _id: ObjectId,
  class_id: String,
  teacher_id: String,
  title: String,
  description: String,
  due_date: DateTime,
  max_points: Number,
  created_at: DateTime,
  is_active: Boolean
}
```

### Submissions Collection
```javascript
{
  _id: ObjectId,
  assignment_id: String,
  student_id: String,
  content: String,
  file_url: String,
  submitted_at: DateTime,
  status: String
}
```

### Grades Collection
```javascript
{
  _id: ObjectId,
  student_id: String,
  assignment_id: String,
  points: Number,
  feedback: String,
  graded_by: String,
  graded_at: DateTime
}
```

### Announcements Collection
```javascript
{
  _id: ObjectId,
  class_id: String,
  teacher_id: String,
  title: String,
  content: String,
  created_at: DateTime
}
```

## 🔒 Security Features

- ✅ Password hashing using SHA-256
- ✅ Secure session tokens
- ✅ Token expiration (24 hours default)
- ✅ Password reset with time-limited tokens
- ✅ Session validation for protected routes
- ✅ Unique email constraint
- ✅ User role management

## 🧪 Testing the Database

Run the database test script:

```powershell
python data_base.py
```

This will test:
- Database connection
- User creation
- Authentication
- Session creation

## 📝 Notes

- All passwords are hashed before storage
- Sessions automatically expire after 24 hours (configurable)
- Reset tokens expire after 1 hour
- All timestamps are stored in UTC
- MongoDB indexes are automatically created for performance
- Email addresses are case-insensitive

## 🛠️ Troubleshooting

### MongoDB Connection Error
```
❌ Failed to connect to MongoDB
```
**Solution:** Make sure MongoDB is running:
```powershell
net start MongoDB
```

### Import Error: pymongo
```
Import "pymongo" could not be resolved
```
**Solution:** Install dependencies:
```powershell
pip install pymongo
```

### Database Not Found
**Solution:** MongoDB creates databases automatically on first write. No manual creation needed.

## 📚 Additional Resources

- [MongoDB Documentation](https://docs.mongodb.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [PyMongo Documentation](https://pymongo.readthedocs.io/)

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

MIT License - feel free to use this project for learning and development.
