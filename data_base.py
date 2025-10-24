"""
MongoDB Database System for Student-Teacher Website
This module handles all database operations including user management, authentication, and data persistence.
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, ConnectionFailure, PyMongoError
from pymongo import MongoClient, ASCENDING, DESCENDING


class DatabaseManager:
    """Main database manager class for MongoDB operations"""
    def __init__(self, connection_string: str = None, database_name: str = "student_teacher_db"):
        """
        Initialize database connection
        
        Args:
            connection_string: MongoDB connection URI (default: localhost)
            database_name: Name of the database to use
        """
        if connection_string is None:
            connection_string = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.server_info()
            self.db = self.client[database_name]
            self._setup_collections()
            print(f"✅ Successfully connected to MongoDB database: {database_name}")
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def _setup_collections(self):
        """Setup collections and create indexes"""
        # Users collection
        self.users = self.db.users
        self.users.create_index([("email", ASCENDING)], unique=True)
        self.users.create_index([("username", ASCENDING)])
        self.users.create_index([("role", ASCENDING)], sparse=True)
        
        # Sessions collection for login sessions
        self.sessions = self.db.sessions
        self.sessions.create_index([("user_id", ASCENDING)])
        self.sessions.create_index([("token", ASCENDING)], unique=True)
        self.sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
        
        # Password reset tokens
        self.reset_tokens = self.db.reset_tokens
        self.reset_tokens.create_index([("email", ASCENDING)])
        self.reset_tokens.create_index([("token", ASCENDING)], unique=True)
        self.reset_tokens.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
        
        # Classes/Subjects collection
        self.classes = self.db.classes
        self.classes.create_index([("class_name", ASCENDING)])
        self.classes.create_index([("teacher_id", ASCENDING)])
        
        # Assignments collection
        self.assignments = self.db.assignments
        self.assignments.create_index([("class_id", ASCENDING)])
        self.assignments.create_index([("teacher_id", ASCENDING)])
        self.assignments.create_index([("due_date", ASCENDING)])
        
        # Submissions collection
        self.submissions = self.db.submissions
        self.submissions.create_index([("assignment_id", ASCENDING)])
        self.submissions.create_index([("student_id", ASCENDING)])
        self.submissions.create_index([("submitted_at", DESCENDING)])
        
        # Announcements collection
        self.announcements = self.db.announcements
        self.announcements.create_index([("class_id", ASCENDING)])
        self.announcements.create_index([("created_at", DESCENDING)])
        
        # Grades collection
        self.grades = self.db.grades
        self.grades.create_index([("student_id", ASCENDING)])
        self.grades.create_index([("assignment_id", ASCENDING)])
        
        # Private Teachers/Coaching collection (for students)
        self.private_teachers = self.db.private_teachers
        self.private_teachers.create_index([("user_id", ASCENDING)])
        self.private_teachers.create_index([("created_at", DESCENDING)])
        
        # Exams collection (for courses)
        self.exams = self.db.exams
        self.exams.create_index([("course_id", ASCENDING)])
        self.exams.create_index([("created_by", ASCENDING)])
        self.exams.create_index([("start_date", ASCENDING)])
        
        # Exam Results collection
        self.exam_results = self.db.exam_results
        self.exam_results.create_index([("exam_id", ASCENDING)])
        self.exam_results.create_index([("student_id", ASCENDING)])
        self.exam_results.create_index([("course_id", ASCENDING)])
        self.exam_results.create_index([("submitted_at", DESCENDING)])
        
        # Public Exams collection (shareable exams without login)
        self.public_exams = self.db.public_exams
        self.public_exams.create_index([("created_by", ASCENDING)])
        self.public_exams.create_index([("created_at", DESCENDING)])
        
        # Guest Exam Submissions collection
        self.guest_submissions = self.db.guest_submissions
        self.guest_submissions.create_index([("exam_id", ASCENDING)])
        self.guest_submissions.create_index([("student_email", ASCENDING)])
        self.guest_submissions.create_index([("submitted_at", DESCENDING)])
        
        # Course Enrollments collection (links students to teacher courses)
        self.enrollments = self.db.enrollments
        self.enrollments.create_index([("course_id", ASCENDING)])
        self.enrollments.create_index([("student_id", ASCENDING)])
        self.enrollments.create_index([("enrolled_at", DESCENDING)])
        # Ensure unique enrollment per student per course
        self.enrollments.create_index([("course_id", ASCENDING), ("student_id", ASCENDING)], unique=True)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(self, username: str, email: str, password: str,role: str = "student",
                    class_subject: str = None) -> Dict:
        """
        Create a new user in the database
        
        Args:
            username: User's display name
            email: User's email (must be unique)
            password: Plain text password (will be hashed)
            role: User's role number (for students) or employee ID (for teachers)
            user_type: "student" or "teacher"
            class_subject: Class or subject (optional)
        
        Returns:
            Dictionary with user_id and success status
        """
        try:
            user_doc = {
                "username": username,
                "email": email.lower(),
                "password": self.hash_password(password),
                "role": role.lower(),
                "class_subject": class_subject,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "profile_complete": False
            }
            
            result = self.users.insert_one(user_doc)
            return {
                "success": True,
                "user_id": str(result.inserted_id),
                "message": "User created successfully"
            }
        except DuplicateKeyError:
            return {
                "success": False,
                "message": "Email already exists"
            }
        except PyMongoError as e:
            return {
                "success": False,
                "message": f"Error creating user: {str(e)}"
            }
        

    def preferences_data(self, email: str, role:str = "student", class_subject:str = None) -> Optional[Dict]:
        """"sumary_line
        
        Keyword arguments:
        argument -- description
        Return: return_description
        """        
        try:
            update_fields = {
                "role": role.lower(),
                "class_subject": class_subject,
                "updated_at": datetime.utcnow()
            }
            
            result = self.users.update_one(
                {"email": email.lower()},
                {"$set": update_fields}
            )
            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Preferences updated successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "No changes made to preferences"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating preferences: {str(e)}"
            }

    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with email and password
        
        Args:
            email: User's email
            password: Plain text password
        
        Returns:
            User document if authenticated, None otherwise
        """
        hashed_password = self.hash_password(password)
        user = self.users.find_one({
            "email": email.lower(),
            "password": hashed_password,
            "is_active": True
        })
        
        if user:
            # Remove password from returned data
            user.pop("password", None)
            user["_id"] = str(user["_id"])
            return user
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user.pop("password", None)
                user["_id"] = str(user["_id"])
                return user
        except Exception as e:
            print(f"Error getting user: {e}")
        return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        user = self.users.find_one({"email": email.lower()})
        if user:
            user.pop("password", None)
            user["_id"] = str(user["_id"])
            return user
        return None
    
    def update_user(self, user_id: str, update_fields: Dict) -> bool:
        """
        Update user information
        
        Args:
            user_id: User's ID
            update_fields: Dictionary of fields to update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Don't allow direct password updates through this method
            update_fields.pop("password", None)
            update_fields["updated_at"] = datetime.utcnow()
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_fields}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Soft delete user by setting is_active to False"""
        try:
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    # ==================== SESSION MANAGEMENT ====================
    
    def create_session(self, user_id: str, duration_hours: int = 24) -> Dict:
        """
        Create a new session for user
        
        Args:
            user_id: User's ID
            duration_hours: Session duration in hours
        
        Returns:
            Dictionary with token and expiration time
        """
        try:
            token = self.generate_token()
            expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
            
            session_doc = {
                "user_id": user_id,
                "token": token,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at
            }
            
            self.sessions.insert_one(session_doc)
            
            return {
                "success": True,
                "token": token,
                "expires_at": expires_at.isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating session: {str(e)}"
            }
    
    def validate_session(self, token: str) -> Optional[str]:
        """
        Validate session token and return user_id
        
        Args:
            token: Session token
        
        Returns:
            User ID if valid, None otherwise
        """
        session = self.sessions.find_one({
            "token": token,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        if session:
            return session["user_id"]
        return None
    
    def delete_session(self, token: str) -> bool:
        """Delete (logout) a session"""
        try:
            result = self.sessions.delete_one({"token": token})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def delete_user_sessions(self, user_id: str) -> bool:
        """Delete all sessions for a user"""
        try:
            result = self.sessions.delete_many({"user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting user sessions: {e}")
            return False
    
    # ==================== PASSWORD RESET ====================
    
    def create_reset_token(self, email: str, duration_hours: int = 1) -> Dict:
        """
        Create password reset token
        
        Args:
            email: User's email
            duration_hours: Token validity duration
        
        Returns:
            Dictionary with token and expiration
        """
        try:
            user = self.get_user_by_email(email)
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            token = self.generate_token()
            expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
            
            reset_doc = {
                "email": email.lower(),
                "token": token,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
                "used": False
            }
            
            self.reset_tokens.insert_one(reset_doc)
            
            return {
                "success": True,
                "token": token,
                "expires_at": expires_at.isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating reset token: {str(e)}"
            }
    
    def validate_reset_token(self, token: str) -> Optional[str]:
        """Validate reset token and return email"""
        reset_doc = self.reset_tokens.find_one({
            "token": token,
            "expires_at": {"$gt": datetime.utcnow()},
            "used": False
        })
        
        if reset_doc:
            return reset_doc["email"]
        return None
    
    def reset_password(self, token: str, new_password: str) -> Dict:
        """
        Reset password using token
        
        Args:
            token: Reset token
            new_password: New plain text password
        
        Returns:
            Success status dictionary
        """
        email = self.validate_reset_token(token)
        if not email:
            return {
                "success": False,
                "message": "Invalid or expired token"
            }
        
        try:
            # Update password
            hashed_password = self.hash_password(new_password)
            self.users.update_one(
                {"email": email},
                {"$set": {"password": hashed_password, "updated_at": datetime.utcnow()}}
            )
            
            # Mark token as used
            self.reset_tokens.update_one(
                {"token": token},
                {"$set": {"used": True}}
            )
            
            # Delete all active sessions for this user
            user = self.get_user_by_email(email)
            if user:
                self.delete_user_sessions(user["_id"])
            
            return {
                "success": True,
                "message": "Password reset successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error resetting password: {str(e)}"
            }
    
    # ==================== OAUTH MANAGEMENT ====================
    
    def create_or_update_oauth_user(self, email: str, username: str, 
                                    google_id: str, profile_picture: str = None) -> Dict:
        """
        Create or update user from OAuth (Google) authentication
        
        Args:
            email: User's email from Google
            username: User's name from Google
            google_id: Google user ID
            profile_picture: URL to profile picture
        
        Returns:
            Dictionary with user info and success status
        """
        try:
            # Check if user already exists
            existing_user = self.users.find_one({"email": email.lower()})
            
            if existing_user:
                # Update existing user with Google info
                update_fields = {
                    "google_id": google_id,
                    "updated_at": datetime.utcnow()
                }
                if profile_picture:
                    update_fields["profile_picture"] = profile_picture
                
                self.users.update_one(
                    {"_id": existing_user["_id"]},
                    {"$set": update_fields}
                )
                
                existing_user.pop("password", None)
                existing_user["_id"] = str(existing_user["_id"])
                
                return {
                    "success": True,
                    "user": existing_user,
                    "is_new": False
                }
            else:
                # Create new user
                user_doc = {
                    "username": username,
                    "email": email.lower(),
                    "google_id": google_id,
                    "profile_picture": profile_picture,
                    "user_type": "student",  # Default type
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "is_active": True,
                    "profile_complete": False,
                    "auth_provider": "google"
                }
                
                result = self.users.insert_one(user_doc)
                user_doc["_id"] = str(result.inserted_id)
                user_doc.pop("password", None)
                
                return {
                    "success": True,
                    "user": user_doc,
                    "is_new": True
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating/updating OAuth user: {str(e)}"
            }
    
    def get_user_by_google_id(self, google_id: str) -> Optional[Dict]:
        """Get user by Google ID"""
        user = self.users.find_one({"google_id": google_id})
        if user:
            user.pop("password", None)
            user["_id"] = str(user["_id"])
            return user
        return None
    
    # ==================== CLASS MANAGEMENT ====================
    
    def create_class(self, class_name: str, teacher_id: str, description: str = None,
                    subject: str = None, schedule: Dict = None) -> Dict:
        """Create a new class"""
        try:
            class_doc = {
                "class_name": class_name,
                "teacher_id": teacher_id,
                "description": description,
                "subject": subject,
                "schedule": schedule,
                "students": [],
                "created_at": datetime.utcnow(),
                "is_active": True
            }
            
            result = self.classes.insert_one(class_doc)
            return {
                "success": True,
                "class_id": str(result.inserted_id)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating class: {str(e)}"
            }
    
    def add_student_to_class(self, class_id: str, student_id: str) -> bool:
        """Add a student to a class"""
        try:
            result = self.classes.update_one(
                {"_id": ObjectId(class_id)},
                {"$addToSet": {"students": student_id}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error adding student to class: {e}")
            return False
    
    def get_classes_by_teacher(self, teacher_id: str) -> List[Dict]:
        """Get all classes taught by a teacher"""
        classes = list(self.classes.find({"teacher_id": teacher_id, "is_active": True}))
        for cls in classes:
            cls["_id"] = str(cls["_id"])
        return classes
    
    def get_classes_by_student(self, student_id: str) -> List[Dict]:
        """Get all classes a student is enroleed in"""
        classes = list(self.classes.find({"students": student_id, "is_active": True}))
        for cls in classes:
            cls["_id"] = str(cls["_id"])
        return classes
    
    # ==================== ASSIGNMENT MANAGEMENT ====================
    
    def create_assignment(self, class_id: str, teacher_id: str, title: str,
                         description: str, due_date: datetime, max_points: int = 100) -> Dict:
        """Create a new assignment"""
        try:
            assignment_doc = {
                "class_id": class_id,
                "teacher_id": teacher_id,
                "title": title,
                "description": description,
                "due_date": due_date,
                "max_points": max_points,
                "created_at": datetime.utcnow(),
                "is_active": True
            }
            
            result = self.assignments.insert_one(assignment_doc)
            return {
                "success": True,
                "assignment_id": str(result.inserted_id)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating assignment: {str(e)}"
            }
    
    def submit_assignment(self, assignment_id: str, student_id: str,
                         content: str, file_url: str = None) -> Dict:
        """Submit an assignment"""
        try:
            submission_doc = {
                "assignment_id": assignment_id,
                "student_id": student_id,
                "content": content,
                "file_url": file_url,
                "submitted_at": datetime.utcnow(),
                "status": "submitted"
            }
            
            result = self.submissions.insert_one(submission_doc)
            return {
                "success": True,
                "submission_id": str(result.inserted_id)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error submitting assignment: {str(e)}"
            }
    
    def get_assignment_submissions(self, assignment_id: str) -> List[Dict]:
        """Get all submissions for an assignment"""
        submissions = list(self.submissions.find({"assignment_id": assignment_id}))
        for sub in submissions:
            sub["_id"] = str(sub["_id"])
        return submissions
    
    # ==================== GRADE MANAGEMENT ====================
    
    def add_grade(self, student_id: str, assignment_id: str, points: float,
                 feedback: str = None, graded_by: str = None) -> Dict:
        """Add or update a grade"""
        try:
            grade_doc = {
                "student_id": student_id,
                "assignment_id": assignment_id,
                "points": points,
                "feedback": feedback,
                "graded_by": graded_by,
                "graded_at": datetime.utcnow()
            }
            
            # Upsert: update if exists, insert if not
            result = self.grades.update_one(
                {"student_id": student_id, "assignment_id": assignment_id},
                {"$set": grade_doc},
                upsert=True
            )
            
            return {
                "success": True,
                "message": "Grade added successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error adding grade: {str(e)}"
            }
    
    def get_student_grades(self, student_id: str) -> List[Dict]:
        """Get all grades for a student"""
        grades = list(self.grades.find({"student_id": student_id}))
        for grade in grades:
            grade["_id"] = str(grade["_id"])
        return grades
    
    # ==================== ANNOUNCEMENT MANAGEMENT ====================
    
    def create_announcement(self, class_id: str, teacher_id: str,
                          title: str, content: str) -> Dict:
        """Create a new announcement"""
        try:
            announcement_doc = {
                "class_id": class_id,
                "teacher_id": teacher_id,
                "title": title,
                "content": content,
                "created_at": datetime.utcnow()
            }
            
            result = self.announcements.insert_one(announcement_doc)
            return {
                "success": True,
                "announcement_id": str(result.inserted_id)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating announcement: {str(e)}"
            }
    
    def get_class_announcements(self, class_id: str, limit: int = 10) -> List[Dict]:
        """Get recent announcements for a class"""
        announcements = list(
            self.announcements.find({"class_id": class_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        for ann in announcements:
            ann["_id"] = str(ann["_id"])
        return announcements
    
    # ==================== UTILITY METHODS ====================
    
    def get_all_students(self) -> List[Dict]:
        """Get all students"""
        students = list(self.users.find({"user_type": "student", "is_active": True}))
        for student in students:
            student.pop("password", None)
            student["_id"] = str(student["_id"])
        return students
    
    def get_all_teachers(self) -> List[Dict]:
        """Get all teachers"""
        teachers = list(self.users.find({"user_type": "teacher", "is_active": True}))
        for teacher in teachers:
            teacher.pop("password", None)
            teacher["_id"] = str(teacher["_id"])
        return teachers
    
    # ==================== COURSES/PRIVATE TEACHERS MANAGEMENT ====================
    
    def add_course(self, user_id: str, course_data: Dict) -> Dict:
        """
        Add a new course/private teacher entry for a user
        
        Args:
            user_id: ID of the user adding the course
            course_data: Dictionary containing course information
            
        Returns:
            Dictionary with success status and course ID
        """
        try:
            course_entry = {
                "user_id": user_id,
                "name": course_data.get("name"),
                "teacher_name": course_data.get("teacherName"),
                "subject": course_data.get("subject"),
                "schedule": course_data.get("schedule"),
                "location": course_data.get("location"),
                "contact_info": course_data.get("contactInfo"),
                "fees": course_data.get("fees"),
                "description": course_data.get("description"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = self.private_teachers.insert_one(course_entry)
            
            return {
                "success": True,
                "message": "Course added successfully",
                "course_id": str(result.inserted_id)
            }
        except PyMongoError as e:
            print(f"Error adding course: {e}")
            return {
                "success": False,
                "message": f"Error adding course: {str(e)}"
            }
    
    def get_user_courses(self, user_id: str) -> List[Dict]:
        """
        Get all courses for a specific user
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of course dictionaries
        """
        try:
            courses = list(
                self.private_teachers.find({"user_id": user_id})
                .sort("created_at", DESCENDING)
            )
            
            for course in courses:
                course["_id"] = str(course["_id"])
                course["id"] = str(course["_id"])
                # Format dates
                if "created_at" in course:
                    course["createdAt"] = course["created_at"].strftime("%m/%d/%Y")
                
            return courses
        except PyMongoError as e:
            print(f"Error fetching courses: {e}")
            return []
    
    def update_course(self, course_id: str, user_id: str, course_data: Dict) -> Dict:
        """
        Update an existing course
        
        Args:
            course_id: ID of the course to update
            user_id: ID of the user (for verification)
            course_data: Dictionary containing updated course information
            
        Returns:
            Dictionary with success status
        """
        try:
            update_fields = {
                "name": course_data.get("name"),
                "teacher_name": course_data.get("teacherName"),
                "subject": course_data.get("subject"),
                "schedule": course_data.get("schedule"),
                "location": course_data.get("location"),
                "contact_info": course_data.get("contactInfo"),
                "fees": course_data.get("fees"),
                "description": course_data.get("description"),
                "updated_at": datetime.utcnow()
            }
            
            result = self.private_teachers.update_one(
                {"_id": ObjectId(course_id), "user_id": user_id},
                {"$set": update_fields}
            )
            
            if result.matched_count > 0:
                return {
                    "success": True,
                    "message": "Course updated successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Course not found or unauthorized"
                }
        except PyMongoError as e:
            print(f"Error updating course: {e}")
            return {
                "success": False,
                "message": f"Error updating course: {str(e)}"
            }
    
    def delete_course(self, course_id: str, user_id: str) -> Dict:
        """
        Delete a course
        
        Args:
            course_id: ID of the course to delete
            user_id: ID of the user (for verification)
            
        Returns:
            Dictionary with success status
        """
        try:
            result = self.private_teachers.delete_one(
                {"_id": ObjectId(course_id), "user_id": user_id}
            )
            
            if result.deleted_count > 0:
                return {
                    "success": True,
                    "message": "Course deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Course not found or unauthorized"
                }
        except PyMongoError as e:
            print(f"Error deleting course: {e}")
            return {
                "success": False,
                "message": f"Error deleting course: {str(e)}"
            }
    
    # ==================== COURSE ENROLLMENTS MANAGEMENT ====================
    
    def enroll_student_in_course(self, course_id: str, student_id: str, teacher_id: str) -> Dict:
        """
        Enroll a student in a teacher's course
        
        Args:
            course_id: ID of the course
            student_id: ID of the student to enroll
            teacher_id: ID of the teacher (for verification)
            
        Returns:
            Dictionary with success status
        """
        try:
            # Verify the course belongs to the teacher
            course = self.private_teachers.find_one({
                "_id": ObjectId(course_id),
                "user_id": teacher_id
            })
            
            if not course:
                return {
                    "success": False,
                    "message": "Course not found or unauthorized"
                }
            
            # Verify the student exists
            student = self.users.find_one({
                "_id": ObjectId(student_id),
                "role": "student"
            })
            
            if not student:
                return {
                    "success": False,
                    "message": "Student not found"
                }
            
            # Create enrollment
            enrollment_doc = {
                "course_id": course_id,
                "student_id": student_id,
                "teacher_id": teacher_id,
                "enrolled_at": datetime.utcnow()
            }
            
            result = self.enrollments.insert_one(enrollment_doc)
            
            return {
                "success": True,
                "message": "Student enrolled successfully",
                "enrollment_id": str(result.inserted_id)
            }
        except DuplicateKeyError:
            return {
                "success": False,
                "message": "Student already enrolled in this course"
            }
        except PyMongoError as e:
            print(f"Error enrolling student: {e}")
            return {
                "success": False,
                "message": f"Error enrolling student: {str(e)}"
            }
    
    def unenroll_student_from_course(self, course_id: str, student_id: str, teacher_id: str) -> Dict:
        """
        Remove a student from a course
        
        Args:
            course_id: ID of the course
            student_id: ID of the student to unenroll
            teacher_id: ID of the teacher (for verification)
            
        Returns:
            Dictionary with success status
        """
        try:
            result = self.enrollments.delete_one({
                "course_id": course_id,
                "student_id": student_id,
                "teacher_id": teacher_id
            })
            
            if result.deleted_count > 0:
                return {
                    "success": True,
                    "message": "Student unenrolled successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Enrollment not found"
                }
        except PyMongoError as e:
            print(f"Error unenrolling student: {e}")
            return {
                "success": False,
                "message": f"Error unenrolling student: {str(e)}"
            }
    
    def get_course_enrolled_students(self, course_id: str, teacher_id: str) -> List[Dict]:
        """
        Get all students enrolled in a course
        
        Args:
            course_id: ID of the course
            teacher_id: ID of the teacher (for verification)
            
        Returns:
            List of student dictionaries with enrollment info
        """
        try:
            # Get all enrollments for this course
            enrollments = list(self.enrollments.find({
                "course_id": course_id,
                "teacher_id": teacher_id
            }))
            
            enrolled_students = []
            for enrollment in enrollments:
                # Get student details
                student = self.users.find_one(
                    {"_id": ObjectId(enrollment["student_id"])},
                    {"password": 0}  # Exclude password
                )
                
                if student:
                    student["_id"] = str(student["_id"])
                    student["enrolled_at"] = enrollment["enrolled_at"].isoformat()
                    enrolled_students.append(student)
            
            return enrolled_students
        except PyMongoError as e:
            print(f"Error fetching enrolled students: {e}")
            return []
    
    def get_student_enrolled_courses(self, student_id: str) -> List[Dict]:
        """
        Get all courses a student is enrolled in
        
        Args:
            student_id: ID of the student
            
        Returns:
            List of course dictionaries
        """
        try:
            # Get all enrollments for this student
            enrollments = list(self.enrollments.find({
                "student_id": student_id
            }))
            
            enrolled_courses = []
            for enrollment in enrollments:
                # Get course details
                course = self.private_teachers.find_one({
                    "_id": ObjectId(enrollment["course_id"])
                })
                
                if course:
                    course["_id"] = str(course["_id"])
                    course["id"] = str(course["_id"])
                    course["enrolled_at"] = enrollment["enrolled_at"].isoformat()
                    
                    # Format dates
                    if "created_at" in course:
                        course["createdAt"] = course["created_at"].strftime("%m/%d/%Y")
                    
                    # Get teacher details
                    teacher = self.users.find_one(
                        {"_id": ObjectId(course["user_id"])},
                        {"password": 0}
                    )
                    if teacher:
                        course["teacher_username"] = teacher.get("username", "Unknown")
                        course["teacher_email"] = teacher.get("email", "")
                    
                    enrolled_courses.append(course)
            
            return enrolled_courses
        except PyMongoError as e:
            print(f"Error fetching enrolled courses: {e}")
            return []
    
    def search_students_by_email(self, email_query: str) -> List[Dict]:
        """
        Search for students by email (for enrollment)
        
        Args:
            email_query: Email or partial email to search for
            
        Returns:
            List of student dictionaries
        """
        try:
            students = list(self.users.find(
                {
                    "role": "student",
                    "email": {"$regex": email_query, "$options": "i"}
                },
                {"password": 0}
            ).limit(10))
            
            for student in students:
                student["_id"] = str(student["_id"])
            
            return students
        except PyMongoError as e:
            print(f"Error searching students: {e}")
            return []
    
    # ==================== EXAMS MANAGEMENT ====================
    
    def create_exam(self, course_id: str, user_id: str, exam_data: Dict) -> Dict:
        """
        Create a new exam for a course
        
        Args:
            course_id: ID of the course
            user_id: ID of the user creating the exam
            exam_data: Dictionary containing exam information
            
        Returns:
            Dictionary with success status and exam ID
        """
        try:
            exam_entry = {
                "course_id": course_id,
                "created_by": user_id,
                "title": exam_data.get("title"),
                "description": exam_data.get("description"),
                "duration": exam_data.get("duration"),
                "total_marks": exam_data.get("totalMarks"),
                "start_date": datetime.fromisoformat(exam_data.get("startDate")),
                "end_date": datetime.fromisoformat(exam_data.get("endDate")),
                "instructions": exam_data.get("instructions"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = self.exams.insert_one(exam_entry)
            
            return {
                "success": True,
                "message": "Exam created successfully",
                "exam_id": str(result.inserted_id)
            }
        except PyMongoError as e:
            print(f"Error creating exam: {e}")
            return {
                "success": False,
                "message": f"Error creating exam: {str(e)}"
            }
    
    def get_course_exams(self, course_id: str) -> List[Dict]:
        """
        Get all exams for a specific course
        
        Args:
            course_id: ID of the course
            
        Returns:
            List of exam dictionaries
        """
        try:
            exams = list(
                self.exams.find({"course_id": course_id})
                .sort("start_date", DESCENDING)
            )
            
            for exam in exams:
                exam["_id"] = str(exam["_id"])
                # Format dates to ISO string for frontend
                if "start_date" in exam:
                    exam["start_date"] = exam["start_date"].isoformat()
                if "end_date" in exam:
                    exam["end_date"] = exam["end_date"].isoformat()
                if "created_at" in exam:
                    exam["created_at"] = exam["created_at"].isoformat()
                
            return exams
        except PyMongoError as e:
            print(f"Error fetching exams: {e}")
            return []
    
    def get_exam_by_id(self, exam_id: str) -> Optional[Dict]:
        """
        Get a specific exam by ID with all details including questions
        
        Args:
            exam_id: ID of the exam
            
        Returns:
            Exam dictionary with all details
        """
        try:
            exam = self.exams.find_one({"_id": ObjectId(exam_id)})
            
            if exam:
                exam["_id"] = str(exam["_id"])
                # Format dates
                if "start_date" in exam:
                    exam["start_date"] = exam["start_date"].isoformat()
                if "end_date" in exam:
                    exam["end_date"] = exam["end_date"].isoformat()
                if "created_at" in exam:
                    exam["created_at"] = exam["created_at"].isoformat()
                
                return exam
            return None
        except PyMongoError as e:
            print(f"Error fetching exam: {e}")
            return None
    
    def get_available_exams(self, user_id: str) -> List[Dict]:
        """
        Get all available (active) exams for a student
        Gets exams from all courses the student is enrolled in
        
        Args:
            user_id: ID of the student
            
        Returns:
            List of available exam dictionaries with course info
        """
        try:
            # Get all enrollments for this student
            enrollments = list(self.enrollments.find({"student_id": user_id}))
            course_ids = [enrollment["course_id"] for enrollment in enrollments]
            
            if not course_ids:
                # No enrollments, return empty list
                return []
            
            # Get all exams for enrolled courses
            now = datetime.utcnow()
            exams = list(
                self.exams.find({
                    "course_id": {"$in": course_ids},
                    "start_date": {"$lte": now},
                    "end_date": {"$gte": now}
                }).sort("start_date", DESCENDING)
            )
            
            # Enrich exams with course information
            for exam in exams:
                exam["_id"] = str(exam["_id"])
                
                # Get course details
                course = self.private_teachers.find_one({"_id": ObjectId(exam["course_id"])})
                if course:
                    exam["course_name"] = course.get("name", "Unknown Course")
                    exam["course_subject"] = course.get("subject", "")
                    
                    # Get teacher info
                    teacher = self.users.find_one(
                        {"_id": ObjectId(course["user_id"])},
                        {"password": 0}
                    )
                    if teacher:
                        exam["teacher_name"] = teacher.get("username", "Unknown")
                
                # Format dates
                if "start_date" in exam:
                    exam["start_date"] = exam["start_date"].isoformat()
                if "end_date" in exam:
                    exam["end_date"] = exam["end_date"].isoformat()
                if "created_at" in exam:
                    exam["created_at"] = exam["created_at"].isoformat()
            
            return exams
        except PyMongoError as e:
            print(f"Error fetching available exams: {e}")
            return []
    
    def delete_exam(self, exam_id: str, user_id: str) -> Dict:
        """
        Delete an exam (works for both course-based and public exams)
        
        Args:
            exam_id: ID of the exam to delete
            user_id: ID of the user (for verification)
            
        Returns:
            Dictionary with success status
        """
        try:
            # Try to delete from course exams first
            result = self.exams.delete_one(
                {"_id": ObjectId(exam_id), "created_by": user_id}
            )
            
            # If not found in course exams, try public exams
            if result.deleted_count == 0:
                result = self.public_exams.delete_one(
                    {"_id": ObjectId(exam_id), "created_by": user_id}
                )
            
            if result.deleted_count > 0:
                return {
                    "success": True,
                    "message": "Exam deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Exam not found or unauthorized"
                }
        except PyMongoError as e:
            print(f"Error deleting exam: {e}")
            return {
                "success": False,
                "message": f"Error deleting exam: {str(e)}"
            }
    
    def get_course_assignments(self, course_id: str) -> List[Dict]:
        """Get all assignments for a course (placeholder)"""
        # This would query your assignments collection
        return []
    
    def get_course_announcements_by_course(self, course_id: str) -> List[Dict]:
        """Get all announcements for a course (placeholder)"""
        # This would query your announcements collection
        return []
    
    # ==================== EXAM RESULTS MANAGEMENT ====================
    
    def submit_exam_result(self, exam_id: str, student_id: str, course_id: str, 
                          score: int, total_marks: int, answers: Dict, 
                          submitted_at: str = None) -> Dict:
        """
        Submit exam result for a student
        
        Args:
            exam_id: ID of the exam
            student_id: ID of the student
            course_id: ID of the course
            score: Score obtained
            total_marks: Total marks
            answers: Dictionary of answers
            submitted_at: Submission timestamp
            
        Returns:
            Dictionary with success status
        """
        try:
            # Check if already submitted
            existing = self.exam_results.find_one({
                "exam_id": exam_id,
                "student_id": student_id
            })
            
            if existing:
                return {
                    "success": False,
                    "message": "Exam already submitted"
                }
            
            result_entry = {
                "exam_id": exam_id,
                "student_id": student_id,
                "course_id": course_id,
                "score": score,
                "total_marks": total_marks,
                "percentage": round((score / total_marks) * 100, 2) if total_marks > 0 else 0,
                "answers": answers,
                "submitted_at": datetime.fromisoformat(submitted_at) if submitted_at else datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
            
            result = self.exam_results.insert_one(result_entry)
            
            return {
                "success": True,
                "message": "Exam result submitted successfully",
                "result_id": str(result.inserted_id)
            }
        except PyMongoError as e:
            print(f"Error submitting exam result: {e}")
            return {
                "success": False,
                "message": f"Error submitting result: {str(e)}"
            }
    
    def get_student_exam_results(self, course_id: str, student_id: str) -> List[Dict]:
        """
        Get all exam results for a student in a course
        
        Args:
            course_id: ID of the course
            student_id: ID of the student
            
        Returns:
            List of exam result dictionaries
        """
        try:
            results = list(
                self.exam_results.find({
                    "course_id": course_id,
                    "student_id": student_id
                }).sort("submitted_at", DESCENDING)
            )
            
            for result in results:
                result["_id"] = str(result["_id"])
                if "submitted_at" in result:
                    result["submitted_at"] = result["submitted_at"].isoformat()
                if "created_at" in result:
                    result["created_at"] = result["created_at"].isoformat()
                
            return results
        except PyMongoError as e:
            print(f"Error fetching student exam results: {e}")
            return []
    
    def get_exam_all_results(self, exam_id: str) -> List[Dict]:
        """
        Get all student results for a specific exam (including guest submissions)
        
        Args:
            exam_id: ID of the exam
            
        Returns:
            List of all student results (both registered and guest)
        """
        try:
            # Get regular student results
            results = list(
                self.exam_results.find({"exam_id": exam_id})
                .sort("score", DESCENDING)
            )
            
            for result in results:
                result["_id"] = str(result["_id"])
                result["submission_type"] = "registered"
                if "submitted_at" in result:
                    result["submitted_at"] = result["submitted_at"].isoformat()
                
                # Get student info
                student = self.get_user_by_id(result["student_id"])
                if student:
                    result["student_name"] = student.get("username", "Unknown")
                    result["student_email"] = student.get("email", "")
            
            # Also get guest submissions (from public exam links)
            guest_results = list(
                self.guest_submissions.find({"exam_id": exam_id})
                .sort("score", DESCENDING)
            )
            
            for result in guest_results:
                result["_id"] = str(result["_id"])
                result["submission_type"] = "guest"
                result["student_id"] = result.get("student_email") or result.get("student_phone", "guest")
                
                if "submitted_at" in result:
                    if isinstance(result["submitted_at"], datetime):
                        result["submitted_at"] = result["submitted_at"].isoformat()
                
                # Student info already stored in guest submissions
                if "student_name" not in result:
                    result["student_name"] = result.get("student_info", {}).get("name", "Guest Student")
                if "student_email" not in result:
                    result["student_email"] = result.get("student_info", {}).get("email", "")
                if "student_phone" not in result:
                    result["student_phone"] = result.get("student_info", {}).get("phone", "")
            
            # Combine both lists
            all_results = results + guest_results
            
            # Sort by score descending
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            return all_results
        except PyMongoError as e:
            print(f"Error fetching exam results: {e}")
            return []
    
    def update_exam_result(self, exam_id: str, submission_id: str, student_id: str, 
                          score: int, answers: List[Dict], reviewed: bool = True, 
                          submission_type: str = "registered") -> Dict:
        """
        Update an exam result with teacher's review and modified scores
        Works for both registered students and guest submissions
        
        Args:
            exam_id: ID of the exam
            submission_id: ID of the submission to update
            student_id: ID of the student (or email/phone for guests)
            score: Updated total score
            answers: Updated answers array with teacher feedback
            reviewed: Whether the submission has been reviewed
            submission_type: "registered" or "guest"
            
        Returns:
            Success/failure message
        """
        try:
            # Determine which collection to update
            collection = self.guest_submissions if submission_type == "guest" else self.exam_results
            
            # Find the exam result
            if submission_type == "guest":
                # For guest submissions, we don't check student_id match as strictly
                result = collection.find_one({
                    "_id": ObjectId(submission_id),
                    "exam_id": exam_id
                })
            else:
                result = collection.find_one({
                    "_id": ObjectId(submission_id),
                    "exam_id": exam_id,
                    "student_id": student_id
                })
            
            if not result:
                return {
                    "success": False,
                    "message": f"Exam result not found in {submission_type} submissions"
                }
            
            # Update the result
            update_result = collection.update_one(
                {"_id": ObjectId(submission_id)},
                {
                    "$set": {
                        "score": score,
                        "answers": answers,
                        "reviewed": reviewed,
                        "reviewed_at": datetime.utcnow()
                    }
                }
            )
            
            if update_result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Exam result updated successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "No changes made to exam result"
                }
                
        except PyMongoError as e:
            print(f"Error updating exam result: {e}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}"
            }
    
    def get_exam_result_by_id(self, result_id: str) -> Dict:
        """
        Get an exam result by its ID
        Searches in both exam_results and guest_submissions collections
        
        Args:
            result_id: ID of the result
            
        Returns:
            Result dictionary or None if not found
        """
        try:
            # Try to find in exam_results first
            result = self.exam_results.find_one({"_id": ObjectId(result_id)})
            
            if result:
                result["_id"] = str(result["_id"])
                return result
            
            # Try to find in guest_submissions
            result = self.guest_submissions.find_one({"_id": ObjectId(result_id)})
            
            if result:
                result["_id"] = str(result["_id"])
                return result
            
            return None
                
        except PyMongoError as e:
            print(f"Error getting exam result: {e}")
            return None
    
    def get_all_tests_by_teacher(self, teacher_id: str) -> List[Dict]:
        """
        Get all tests/exams created by a specific teacher (including public exams)
        
        Args:
            teacher_id: ID of the teacher
            
        Returns:
            List of test dictionaries with course info
        """
        try:
            # Get all course-based exams created by this teacher
            course_tests = list(
                self.exams.find({"created_by": teacher_id}).sort("created_at", DESCENDING)
            )
            
            # Get all public exams created by this teacher
            public_tests = list(
                self.public_exams.find({"created_by": teacher_id}).sort("created_at", DESCENDING)
            )
            
            # Combine both lists
            all_tests = course_tests + public_tests
            
            # Sort by created_at descending
            all_tests.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
            
            # Enrich tests with course information
            for test in all_tests:
                test["_id"] = str(test["_id"])
                
                # Determine if it's a public exam or course-based exam
                test["is_public"] = test.get("is_public", False)
                
                # Get course details for course-based exams
                if "course_id" in test and test.get("course_id"):
                    course = self.private_teachers.find_one({"_id": ObjectId(test["course_id"])})
                    if course:
                        test["courseName"] = course.get("name", "Unknown Course")
                        test["courseSubject"] = course.get("subject", "")
                    else:
                        test["courseName"] = "Unknown Course"
                else:
                    # For public exams without course_id
                    if test.get("is_public"):
                        test["courseName"] = "Public Exam (Shareable Link)"
                        test["courseSubject"] = test.get("subject", "")
                    else:
                        test["courseName"] = "No Course"
                
                # Format dates
                if "start_date" in test:
                    test["startDate"] = test["start_date"].isoformat() if isinstance(test["start_date"], datetime) else test["start_date"]
                elif "startDate" in test:
                    # Already in correct format, just ensure it's a string
                    test["startDate"] = test["startDate"] if isinstance(test["startDate"], str) else test["startDate"].isoformat()
                else:
                    # Default to created_at if no start_date
                    test["startDate"] = test.get("created_at", datetime.utcnow()).isoformat()
                
                if "end_date" in test:
                    test["endDate"] = test["end_date"].isoformat() if isinstance(test["end_date"], datetime) else test["end_date"]
                elif "endDate" in test:
                    # Already in correct format
                    test["endDate"] = test["endDate"] if isinstance(test["endDate"], str) else test["endDate"].isoformat()
                else:
                    # Default to 7 days after start if no end_date
                    start = test.get("created_at", datetime.utcnow())
                    test["endDate"] = (start + timedelta(days=7)).isoformat()
                
                if "created_at" in test:
                    test["createdAt"] = test["created_at"].isoformat() if isinstance(test["created_at"], datetime) else test["created_at"]
                
                # Clean up old keys
                test.pop("start_date", None)
                test.pop("end_date", None)
                test.pop("created_at", None)
            
            print(f"Found {len(all_tests)} total tests for teacher {teacher_id} (Course: {len(course_tests)}, Public: {len(public_tests)})")
            return all_tests
        except PyMongoError as e:
            print(f"Error fetching teacher tests: {e}")
            return []
    
    def duplicate_test(self, test_id: str, user_id: str) -> Dict:
        """
        Duplicate an existing test/exam (works for both course-based and public exams)
        
        Args:
            test_id: ID of the test to duplicate
            user_id: ID of the user (for verification)
            
        Returns:
            Dictionary with success status and new test ID
        """
        try:
            # Try to find the test in course exams first
            original_test = self.exams.find_one({
                "_id": ObjectId(test_id),
                "created_by": user_id
            })
            
            target_collection = self.exams
            
            # If not found, try public exams
            if not original_test:
                original_test = self.public_exams.find_one({
                    "_id": ObjectId(test_id),
                    "created_by": user_id
                })
                target_collection = self.public_exams
            
            if not original_test:
                return {
                    "success": False,
                    "message": "Test not found or unauthorized"
                }
            
            # Create a copy
            new_test = original_test.copy()
            new_test.pop("_id")  # Remove the original ID
            
            # Update title to indicate it's a copy
            new_test["title"] = f"{original_test.get('title', 'Test')} (Copy)"
            
            # Update dates to current time
            new_test["created_at"] = datetime.utcnow()
            
            # Insert the duplicate into the same collection as the original
            result = target_collection.insert_one(new_test)
            
            if result.inserted_id:
                return {
                    "success": True,
                    "message": "Test duplicated successfully",
                    "test_id": str(result.inserted_id)
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to duplicate test"
                }
        except PyMongoError as e:
            print(f"Error duplicating test: {e}")
            return {
                "success": False,
                "message": f"Error duplicating test: {str(e)}"
            }
    
    def delete_test(self, test_id: str, user_id: str) -> Dict:
        """
        Delete a test/exam (alias for delete_exam)
        
        Args:
            test_id: ID of the test to delete
            user_id: ID of the user (for verification)
            
        Returns:
            Dictionary with success status
        """
        return self.delete_exam(test_id, user_id)
    
    # ==================== PUBLIC EXAMS MANAGEMENT ====================
    
    def create_public_exam(self, exam_data: Dict) -> Dict:
        """
        Create a shareable public exam (no login required for students)
        
        Args:
            exam_data: Exam data including questions
            
        Returns:
            Dictionary with success status and exam ID
        """
        try:
            exam_data["created_at"] = datetime.utcnow()
            exam_data["is_public"] = True
            
            result = self.public_exams.insert_one(exam_data)
            
            if result.inserted_id:
                return {
                    "success": True,
                    "message": "Public exam created successfully",
                    "exam_id": str(result.inserted_id)
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to create public exam"
                }
        except PyMongoError as e:
            print(f"Error creating public exam: {e}")
            return {
                "success": False,
                "message": f"Error creating public exam: {str(e)}"
            }
    
    def get_public_exam(self, exam_id: str) -> Optional[Dict]:
        """
        Get a public exam by ID
        
        Args:
            exam_id: ID of the exam
            
        Returns:
            Exam dictionary or None
        """
        try:
            exam = self.public_exams.find_one({"_id": ObjectId(exam_id)})
            
            if exam:
                exam["_id"] = str(exam["_id"])
                
                # Format dates
                if "created_at" in exam:
                    exam["created_at"] = exam["created_at"].isoformat() if isinstance(exam["created_at"], datetime) else exam["created_at"]
                
                return exam
            return None
        except PyMongoError as e:
            print(f"Error fetching public exam: {e}")
            return None
    
    def submit_guest_exam(self, submission_data: Dict) -> Dict:
        """
        Submit exam results for a guest student (no account)
        
        Args:
            submission_data: Submission data including student info and answers
            
        Returns:
            Dictionary with success status
        """
        try:
            submission_data["submitted_at"] = datetime.utcnow() if "submitted_at" not in submission_data else submission_data["submitted_at"]
            
            # Add email/phone for indexing
            student_info = submission_data.get("student_info", {})
            submission_data["student_email"] = student_info.get("email", "")
            submission_data["student_phone"] = student_info.get("phone", "")
            submission_data["student_name"] = student_info.get("name", "")
            
            result = self.guest_submissions.insert_one(submission_data)
            
            if result.inserted_id:
                return {
                    "success": True,
                    "message": "Exam submitted successfully",
                    "submission_id": str(result.inserted_id)
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to submit exam"
                }
        except PyMongoError as e:
            print(f"Error submitting guest exam: {e}")
            return {
                "success": False,
                "message": f"Error submitting exam: {str(e)}"
            }
    
    def get_guest_submissions_by_exam(self, exam_id: str) -> List[Dict]:
        """
        Get all guest submissions for a specific exam
        
        Args:
            exam_id: ID of the exam
            
        Returns:
            List of submission dictionaries
        """
        try:
            submissions = list(
                self.guest_submissions.find({"exam_id": exam_id}).sort("submitted_at", DESCENDING)
            )
            
            for submission in submissions:
                submission["_id"] = str(submission["_id"])
                
                # Format dates
                if "submitted_at" in submission:
                    submission["submitted_at"] = submission["submitted_at"].isoformat() if isinstance(submission["submitted_at"], datetime) else submission["submitted_at"]
            
            return submissions
        except PyMongoError as e:
            print(f"Error fetching guest submissions: {e}")
            return []
    
    def get_public_exams_by_teacher(self, teacher_id: str) -> List[Dict]:
        """
        Get all public exams created by a teacher
        
        Args:
            teacher_id: ID of the teacher
            
        Returns:
            List of exam dictionaries
        """
        try:
            exams = list(
                self.public_exams.find({"created_by": teacher_id}).sort("created_at", DESCENDING)
            )
            
            for exam in exams:
                exam["_id"] = str(exam["_id"])
                
                # Get submission count
                submission_count = self.guest_submissions.count_documents({"exam_id": str(exam["_id"])})
                exam["submission_count"] = submission_count
                
                # Format dates
                if "created_at" in exam:
                    exam["created_at"] = exam["created_at"].isoformat() if isinstance(exam["created_at"], datetime) else exam["created_at"]
            
            return exams
        except PyMongoError as e:
            print(f"Error fetching public exams: {e}")
            return []
    
    def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("✅ Database connection closed")


# Initialize global database instance
db_manager = None

def get_db_manager(connection_string: str = None) -> DatabaseManager:
    """Get or create database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager(connection_string)
    return db_manager

 
if __name__ == "__main__":
    # Test database connection
    try:
        db = DatabaseManager()
        print("\n🧪 Testing database operations...")
        
        # Test user creation
        result = db.create_user(
            username="Test Student",
            email="test@example.com",
            password="test123",
            # role="STU001",
            class_subject="10th Grade"
        )
        print(f"\nUser Creation: {result}")
        
        # Test authentication
        user = db.authenticate_user("test@example.com", "test123")
        print(f"\nAuthentication: {'Success' if user else 'Failed'}")
        
        # Test session creation
        if user:
            session = db.create_session(user["_id"])
            print(f"\nSession Creation: {session}")
        
        print("\n✅ All tests completed successfully!")
        
        db.close_connection()
        
    except (ConnectionFailure, PyMongoError) as e:
        print(f"\n❌ Error during testing: {e}")