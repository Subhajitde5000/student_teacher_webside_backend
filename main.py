import os
import re
import time
import pprint
import random
import datetime
from textblob import TextBlob
from flask_cors import CORS
from flask import Flask, render_template, request, jsonify, make_response, redirect, session, url_for, send_file
from dotenv import load_dotenv
from data_base import get_db_manager
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
import secrets

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure session for OAuth
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

# Initialize database
db = get_db_manager()

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/auth/google/callback")

# Disable HTTPS requirement for local development (remove in production)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

@app.route("/api/sign_up", methods=["POST"])
def sign_up():
    """User registration endpoint"""
    try:
        data = request.get_json()
        print(data)
        
        # Validate required fields
        required_fields = ["username", "email", "password"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        print(f"Received sign up data: {data}")
        
        # Create user in database
        result = db.create_user(
            username=username,
            email=email,
            password=password
        )
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": "User registered successfully",
                "user_id": result["user_id"]
            }), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in sign_up: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/api/preferences", methods=["POST"])
def preferences():
    try:
        data = request.get_json()
        requested_fields = ["role", "class_subject"]
        if not all(field in data for field in requested_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        email = data.get("email")
        role = data.get("role")
        class_subject = data.get("class_subject")
        print(data,"\n")
        # Update user preferences in the database
        result = db.preferences_data(email=email, role=role, class_subject=class_subject)

        if result:
            return jsonify({"success": True, "message": "Preferences updated successfully"}), 200
        else:
            return jsonify({"success": False, "message": "Failed to update preferences"}), 500
    except Exception as e:
        print(f"Error in preferences: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/api/login", methods=["POST"])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data or "email" not in data or "password" not in data:
            return jsonify({"success": False, "message": "Email and password required"}), 400
        
        email = data.get("email")
        password = data.get("password")
        
        # Authenticate user
        user = db.authenticate_user(email, password)
        
        if user:
            # Create session
            session_result = db.create_session(user["_id"])
            
            if session_result["success"]:
                return jsonify({
                    "success": True,
                    "message": "Login successful",
                    "token": session_result["token"],
                    "user": user,
                    "expires_at": session_result["expires_at"]
                }), 200
            else:
                return jsonify({"success": False, "message": "Failed to create session"}), 500
        else:
            return jsonify({"success": False, "message": "Invalid email or password"}), 401
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/api/logout", methods=["POST"])
def logout():
    """User logout endpoint"""
    try:
        data = request.get_json()
        token = data.get("token")
        
        if not token:
            return jsonify({"success": False, "message": "Token required"}), 400
        
        result = db.delete_session(token)
        
        if result:
            return jsonify({"success": True, "message": "Logged out successfully"}), 200
        else:
            return jsonify({"success": False, "message": "Invalid token"}), 400
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/forgot_password", methods=["POST"])
def forget_password():
    """Request password reset endpoint"""
    try:
        data = request.get_json()
        
        if not data or "email" not in data:
            return jsonify({"success": False, "message": "Email required"}), 400
        
        email = data.get("email")
        
        # Create reset token
        result = db.create_reset_token(email)
        
        if result["success"]:
            # In production, you would send this token via email
            # For now, we'll return it in the response
            return jsonify({
                "success": True,
                "message": "Reset token created. Check your email.",
                "token": result["token"],  # Remove this in production
                "expires_at": result["expires_at"]
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/api/reset_password", methods=["POST"])
def reset_password():
    """Reset password using token"""
    try:
        data = request.get_json()
        
        if not data or "token" not in data or "new_password" not in data:
            return jsonify({"success": False, "message": "Token and new password required"}), 400
        
        token = data.get("token")
        new_password = data.get("new_password")
        
        # Reset password
        result = db.reset_password(token, new_password)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/user/<user_id>", methods=["GET"])
def get_user(user_id):
    """Get user information"""
    try:
        user = db.get_user_by_id(user_id)
        
        if user:
            return jsonify({"success": True, "user": user}), 200
        else:
            return jsonify({"success": False, "message": "User not found"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/user/<user_id>", methods=["PUT"])
def update_user(user_id):
    """Update user information"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        result = db.update_user(user_id, data)
        
        if result:
            return jsonify({"success": True, "message": "User updated successfully"}), 200
        else:
            return jsonify({"success": False, "message": "Failed to update user"}), 400
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/students", methods=["GET"])
def get_students():
    """Get all students"""
    try:
        students = db.get_all_students()
        return jsonify({"success": True, "students": students}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/teachers", methods=["GET"])
def get_teachers():
    """Get all teachers"""
    try:
        teachers = db.get_all_teachers()
        return jsonify({"success": True, "teachers": teachers}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== CLASS ENDPOINTS ====================

# @app.route("/api/class", methods=["POST"])
# def create_class():
#     """Create a new class"""
#     try:
#         data = request.get_json()
        
#         required_fields = ["class_name", "teacher_id"]
#         if not all(field in data for field in required_fields):
#             return jsonify({"success": False, "message": "Missing required fields"}), 400
        
#         result = db.create_class(
#             class_name=data.get("class_name"),
#             teacher_id=data.get("teacher_id"),
#             description=data.get("description"),
#             subject=data.get("subject"),
#             schedule=data.get("schedule")
#         )
        
#         return jsonify(result), 201 if result["success"] else 400
        
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# @app.route("/api/class/<class_id>/student/<student_id>", methods=["POST"])
# def add_student_to_class(class_id, student_id):
#     """Add student to a class"""
#     try:
#         result = db.add_student_to_class(class_id, student_id)
        
#         if result:
#             return jsonify({"success": True, "message": "Student added to class"}), 200
#         else:
#             return jsonify({"success": False, "message": "Failed to add student"}), 400
            
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# @app.route("/api/teacher/<teacher_id>/classes", methods=["GET"])
# def get_teacher_classes(teacher_id):
#     """Get all classes for a teacher"""
#     try:
#         classes = db.get_classes_by_teacher(teacher_id)
#         return jsonify({"success": True, "classes": classes}), 200
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# @app.route("/api/student/<student_id>/classes", methods=["GET"])
# def get_student_classes(student_id):
#     """Get all classes for a student"""
#     try:
#         classes = db.get_classes_by_student(student_id)
#         return jsonify({"success": True, "classes": classes}), 200
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== ASSIGNMENT ENDPOINTS ====================

@app.route("/api/assignment", methods=["POST"])
def create_assignment():
    """Create a new assignment"""
    try:
        data = request.get_json()
        
        required_fields = ["class_id", "teacher_id", "title", "description", "due_date"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        # Convert due_date string to datetime
        due_date = datetime.datetime.fromisoformat(data.get("due_date").replace('Z', '+00:00'))
        
        result = db.create_assignment(
            class_id=data.get("class_id"),
            teacher_id=data.get("teacher_id"),
            title=data.get("title"),
            description=data.get("description"),
            due_date=due_date,
            max_points=data.get("max_points", 100)
        )
        
        return jsonify(result), 201 if result["success"] else 400
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/assignment/<assignment_id>/submit", methods=["POST"])
def submit_assignment(assignment_id):
    """Submit an assignment"""
    try:
        data = request.get_json()
        
        if not data or "student_id" not in data or "content" not in data:
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        result = db.submit_assignment(
            assignment_id=assignment_id,
            student_id=data.get("student_id"),
            content=data.get("content"),
            file_url=data.get("file_url")
        )
        
        return jsonify(result), 201 if result["success"] else 400
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/assignment/<assignment_id>/submissions", methods=["GET"])
def get_submissions(assignment_id):
    """Get all submissions for an assignment"""
    try:
        submissions = db.get_assignment_submissions(assignment_id)
        return jsonify({"success": True, "submissions": submissions}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== GRADE ENDPOINTS ====================

@app.route("/api/grade", methods=["POST"])
def add_grade():
    """Add or update a grade"""
    try:
        data = request.get_json()
        
        required_fields = ["student_id", "assignment_id", "points"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        result = db.add_grade(
            student_id=data.get("student_id"),
            assignment_id=data.get("assignment_id"),
            points=data.get("points"),
            feedback=data.get("feedback"),
            graded_by=data.get("graded_by")
        )
        
        return jsonify(result), 200 if result["success"] else 400
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/student/<student_id>/grades", methods=["GET"])
def get_student_grades(student_id):
    """Get all grades for a student"""
    try:
        grades = db.get_student_grades(student_id)
        return jsonify({"success": True, "grades": grades}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== ANNOUNCEMENT ENDPOINTS ====================

@app.route("/api/announcement", methods=["POST"])
def create_announcement():
    """Create a new announcement"""
    try:
        data = request.get_json()
        
        required_fields = ["class_id", "teacher_id", "title", "content"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        result = db.create_announcement(
            class_id=data.get("class_id"),
            teacher_id=data.get("teacher_id"),
            title=data.get("title"),
            content=data.get("content")
        )
        
        return jsonify(result), 201 if result["success"] else 400
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/class/<class_id>/announcements", methods=["GET"])
def get_announcements(class_id):
    """Get announcements for a class"""
    try:
        limit = request.args.get("limit", 10, type=int)
        announcements = db.get_class_announcements(class_id, limit)
        return jsonify({"success": True, "announcements": announcements}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== COURSES/PRIVATE TEACHERS ENDPOINTS ====================

@app.route("/api/courses", methods=["POST"])
def add_course():
    """Add a new course/private teacher for a user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or "user_id" not in data:
            return jsonify({"success": False, "message": "User ID is required"}), 400
        
        user_id = data.get("user_id")
        course_data = data.get("course_data", {})
        
        # Validate required course fields
        if not course_data.get("name") or not course_data.get("subject"):
            return jsonify({"success": False, "message": "Course name and subject are required"}), 400
        
        result = db.add_course(user_id, course_data)
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in add_course: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<user_id>", methods=["GET"])
def get_user_courses(user_id):
    """Get all courses for a specific user"""
    try:
        courses = db.get_user_courses(user_id)
        return jsonify({"success": True, "courses": courses}), 200
    except Exception as e:
        print(f"Error in get_user_courses: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<course_id>", methods=["PUT"])
def update_course(course_id):
    """Update an existing course"""
    try:
        data = request.get_json()
        
        if not data or "user_id" not in data:
            return jsonify({"success": False, "message": "User ID is required"}), 400
        
        user_id = data.get("user_id")
        course_data = data.get("course_data", {})
        
        result = db.update_course(course_id, user_id, course_data)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in update_course: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<course_id>", methods=["DELETE"])
def delete_course(course_id):
    """Delete a course"""
    try:
        data = request.get_json()
        
        if not data or "user_id" not in data:
            return jsonify({"success": False, "message": "User ID is required"}), 400
        
        user_id = data.get("user_id")
        
        result = db.delete_course(course_id, user_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in delete_course: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== COURSE ENROLLMENTS ENDPOINTS ====================

@app.route("/api/courses/<course_id>/enroll", methods=["POST"])
def enroll_student(course_id):
    """Enroll a student in a course"""
    try:
        data = request.get_json()
        
        if not data or "student_id" not in data or "teacher_id" not in data:
            return jsonify({"success": False, "message": "Student ID and Teacher ID are required"}), 400
        
        student_id = data.get("student_id")
        teacher_id = data.get("teacher_id")
        
        result = db.enroll_student_in_course(course_id, student_id, teacher_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in enroll_student: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<course_id>/unenroll", methods=["POST"])
def unenroll_student(course_id):
    """Remove a student from a course"""
    try:
        data = request.get_json()
        
        if not data or "student_id" not in data or "teacher_id" not in data:
            return jsonify({"success": False, "message": "Student ID and Teacher ID are required"}), 400
        
        student_id = data.get("student_id")
        teacher_id = data.get("teacher_id")
        
        result = db.unenroll_student_from_course(course_id, student_id, teacher_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in unenroll_student: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<course_id>/students", methods=["GET"])
def get_enrolled_students(course_id):
    """Get all students enrolled in a course"""
    try:
        teacher_id = request.args.get("teacher_id")
        
        if not teacher_id:
            return jsonify({"success": False, "message": "Teacher ID is required"}), 400
        
        students = db.get_course_enrolled_students(course_id, teacher_id)
        return jsonify({"success": True, "students": students}), 200
        
    except Exception as e:
        print(f"Error in get_enrolled_students: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/students/enrolled-courses", methods=["GET"])
def get_student_enrolled_courses():
    """Get all courses a student is enrolled in"""
    try:
        student_id = request.args.get("student_id")
        
        if not student_id:
            return jsonify({"success": False, "message": "Student ID is required"}), 400
        
        courses = db.get_student_enrolled_courses(student_id)
        return jsonify({"success": True, "courses": courses}), 200
        
    except Exception as e:
        print(f"Error in get_student_enrolled_courses: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/students/search", methods=["GET"])
def search_students():
    """Search for students by email"""
    try:
        email_query = request.args.get("email", "")
        
        if not email_query:
            return jsonify({"success": False, "message": "Email query is required"}), 400
        
        students = db.search_students_by_email(email_query)
        return jsonify({"success": True, "students": students}), 200
        
    except Exception as e:
        print(f"Error in search_students: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== EXAMS ENDPOINTS ====================

@app.route("/api/courses/<course_id>/exams", methods=["POST"])
def create_exam(course_id):
    """Create a new exam for a course"""
    try:
        data = request.get_json()
        
        if not data or "user_id" not in data:
            return jsonify({"success": False, "message": "User ID is required"}), 400
        
        user_id = data.get("user_id")
        exam_data = data.get("exam_data", {})
        
        # Validate required exam fields
        required_fields = ["title", "duration", "totalMarks", "startDate", "endDate"]
        if not all(exam_data.get(field) for field in required_fields):
            return jsonify({"success": False, "message": "Missing required exam fields"}), 400
        
        result = db.create_exam(course_id, user_id, exam_data)
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in create_exam: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<course_id>/exams", methods=["GET"])
def get_course_exams(course_id):
    """Get all exams for a course"""
    try:
        exams = db.get_course_exams(course_id)
        return jsonify({"success": True, "exams": exams}), 200
    except Exception as e:
        print(f"Error in get_course_exams: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/exams/<exam_id>", methods=["GET"])
def get_exam_by_id(exam_id):
    """Get a specific exam with all details including questions"""
    try:
        exam = db.get_exam_by_id(exam_id)
        if exam:
            return jsonify({"success": True, "exam": exam}), 200
        else:
            return jsonify({"success": False, "message": "Exam not found"}), 404
    except Exception as e:
        print(f"Error in get_exam_by_id: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/exams/available", methods=["GET"])
def get_available_exams():
    """Get all available (active) exams for students"""
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User ID is required"}), 400
        
        exams = db.get_available_exams(user_id)
        return jsonify({"success": True, "exams": exams}), 200
    except Exception as e:
        print(f"Error in get_available_exams: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<course_id>/exams/<exam_id>", methods=["DELETE"])
def delete_exam(course_id, exam_id):
    """Delete an exam"""
    try:
        data = request.get_json()
        
        if not data or "user_id" not in data:
            return jsonify({"success": False, "message": "User ID is required"}), 400
        
        user_id = data.get("user_id")
        
        result = db.delete_exam(exam_id, user_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in delete_exam: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<course_id>/assignments", methods=["GET"])
def get_course_assignments(course_id):
    """Get all assignments for a course"""
    try:
        assignments = db.get_course_assignments(course_id)
        return jsonify({"success": True, "assignments": assignments}), 200
    except Exception as e:
        print(f"Error in get_course_assignments: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<course_id>/announcements", methods=["GET"])
def get_course_announcements(course_id):
    """Get all announcements for a course"""
    try:
        announcements = db.get_course_announcements_by_course(course_id)
        return jsonify({"success": True, "announcements": announcements}), 200
    except Exception as e:
        print(f"Error in get_course_announcements: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== EXAM RESULTS ENDPOINTS ====================

@app.route("/api/exams/<exam_id>/submit", methods=["POST"])
def submit_exam_result(exam_id):
    """Submit exam results for a student"""
    try:
        data = request.get_json()
        
        required_fields = ["student_id", "course_id", "score", "total_marks"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        result = db.submit_exam_result(
            exam_id=exam_id,
            student_id=data.get("student_id"),
            course_id=data.get("course_id"),
            score=data.get("score"),
            total_marks=data.get("total_marks"),
            answers=data.get("answers", {}),
            submitted_at=data.get("submitted_at")
        )
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in submit_exam_result: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/courses/<course_id>/results/<student_id>", methods=["GET"])
def get_student_exam_results(course_id, student_id):
    """Get all exam results for a student in a course"""
    try:
        results = db.get_student_exam_results(course_id, student_id)
        return jsonify({"success": True, "results": results}), 200
    except Exception as e:
        print(f"Error in get_student_exam_results: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/exams/<exam_id>/results", methods=["GET"])
def get_exam_all_results(exam_id):
    """Get all student results for a specific exam (teacher view)"""
    try:
        results = db.get_exam_all_results(exam_id)
        return jsonify({"success": True, "results": results}), 200
    except Exception as e:
        print(f"Error in get_exam_all_results: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/exams/<exam_id>/update-result", methods=["PUT"])
def update_exam_result(exam_id):
    """Update exam result with teacher's review and modified scores"""
    try:
        data = request.get_json()
        
        required_fields = ["submission_id", "student_id", "score", "answers"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        result = db.update_exam_result(
            exam_id=exam_id,
            submission_id=data.get("submission_id"),
            student_id=data.get("student_id"),
            score=data.get("score"),
            answers=data.get("answers"),
            reviewed=data.get("reviewed", True),
            submission_type=data.get("submission_type", "registered")  # Support both registered and guest
        )
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in update_exam_result: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/exams/<exam_id>/generate-report", methods=["POST"])
def generate_grade_report(exam_id):
    """Generate a PDF grade report for a student submission"""
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        
        data = request.get_json()
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("<b>GRADE REPORT</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Student Info
        info_data = [
            ['Student Name:', data.get('student_name', 'N/A')],
            ['Exam Title:', data.get('exam_title', 'N/A')],
            ['Score:', f"{data.get('score', 0)} / {data.get('total_marks', 0)}"],
            ['Percentage:', f"{(data.get('score', 0) / max(data.get('total_marks', 1), 1) * 100):.1f}%"]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Footer
        footer = Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal'])
        elements.append(footer)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Grade_Report_{data.get('student_name', 'Student')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({"success": False, "message": f"Failed to generate report: {str(e)}"}), 500


@app.route("/api/exams/<exam_id>/send-report", methods=["POST"])
def send_grade_report(exam_id):
    """Send grade report to student via WhatsApp or Email"""
    try:
        data = request.get_json()
        
        contact_method = data.get('contact_method', 'Email')
        student_name = data.get('student_name', 'Student')
        exam_title = data.get('exam_title', 'Exam')
        score = data.get('score', 0)
        total_marks = data.get('total_marks', 0)
        percentage = (score / max(total_marks, 1) * 100)
        
        if contact_method == 'WhatsApp' and data.get('student_phone'):
            phone = data.get('student_phone')
            # In production, integrate with WhatsApp Business API
            # For now, return success message
            return jsonify({
                "success": True,
                "message": f"Report notification sent to {phone} via WhatsApp",
                "method": "WhatsApp"
            }), 200
            
        elif data.get('student_email'):
            email = data.get('student_email')
            # In production, integrate with email service
            # For now, return success message
            return jsonify({
                "success": True,
                "message": f"Report sent to {email}",
                "method": "Email"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "No valid contact method available"
            }), 400
            
    except Exception as e:
        print(f"Error sending report: {e}")
        return jsonify({"success": False, "message": f"Failed to send report: {str(e)}"}), 500


@app.route("/api/exams/<exam_id>/download-report/<result_id>", methods=["GET"])
def download_student_report(exam_id, result_id):
    """Allow students to download their own grade report"""
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        
        # Get result from database
        result = db.get_exam_result_by_id(result_id)
        
        if not result:
            return jsonify({"success": False, "message": "Result not found"}), 404
        
        if not result.get('reviewed'):
            return jsonify({"success": False, "message": "Result not yet reviewed by teacher"}), 403
        
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("<b>GRADE REPORT</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Student Info
        elements.append(Paragraph(f"<b>Exam:</b> {result.get('exam_title', 'N/A')}", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"<b>Score:</b> {result.get('score', 0)} / {result.get('total_marks', 0)}", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        percentage = (result.get('score', 0) / max(result.get('total_marks', 1), 1) * 100)
        elements.append(Paragraph(f"<b>Percentage:</b> {percentage:.1f}%", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Grade_Report_{result.get('exam_title', 'Exam')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error downloading report: {e}")
        return jsonify({"success": False, "message": f"Failed to download report: {str(e)}"}), 500


# ==================== ALL TESTS ENDPOINTS ====================

@app.route("/api/teacher/<teacher_id>/tests", methods=["GET"])
def get_teacher_all_tests(teacher_id):
    """Get all tests created by a teacher"""
    try:
        print(f"Fetching tests for teacher ID: {teacher_id}")
        tests = db.get_all_tests_by_teacher(teacher_id)
        pprint.pprint(tests)

        return jsonify({"success": True, "tests": tests}), 200
    except Exception as e:
        print(f"Error in get_teacher_all_tests: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/tests/<test_id>/duplicate", methods=["POST"])
def duplicate_test(test_id):
    """Duplicate an existing test"""
    try:
        data = request.get_json()
        
        if not data or "user_id" not in data:
            return jsonify({"success": False, "message": "Missing user_id"}), 400
        
        user_id = data.get("user_id")
        
        result = db.duplicate_test(test_id, user_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in duplicate_test: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/tests/<test_id>", methods=["DELETE"])
def delete_test(test_id):
    """Delete a test"""
    try:
        data = request.get_json()
        
        if not data or "user_id" not in data:
            return jsonify({"success": False, "message": "Missing user_id"}), 400
        
        user_id = data.get("user_id")
        
        result = db.delete_test(test_id, user_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in delete_test: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== PUBLIC EXAMS ENDPOINTS ====================

@app.route("/api/public-exams", methods=["POST"])
def create_public_exam():
    """Create a shareable public exam"""
    try:
        data = request.get_json()
        pprint.pprint(data)
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        result = db.create_public_exam(data)
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in create_public_exam: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/public-exams/<exam_id>", methods=["GET"])
def get_public_exam(exam_id):
    """Get a public exam by ID (for students to take)"""
    try:
        exam = db.get_public_exam(exam_id)
        
        if exam:
            return jsonify({"success": True, "exam": exam}), 200
        else:
            return jsonify({"success": False, "message": "Exam not found"}), 404
            
    except Exception as e:
        print(f"Error in get_public_exam: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/public-exams/submit", methods=["POST"])
def submit_guest_exam():
    """Submit exam results for a guest student"""
    try:
        data = request.get_json()
        pprint.pprint(data)
        
        required_fields = ["exam_id", "student_info", "answers"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        result = db.submit_guest_exam(data)
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in submit_guest_exam: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/public-exams/<exam_id>/submissions", methods=["GET"])
def get_guest_submissions(exam_id):
    """Get all guest submissions for an exam (teacher view)"""
    try:
        submissions = db.get_guest_submissions_by_exam(exam_id)
        return jsonify({"success": True, "submissions": submissions}), 200
    except Exception as e:
        print(f"Error in get_guest_submissions: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/teacher/<teacher_id>/public-exams", methods=["GET"])
def get_teacher_public_exams(teacher_id):
    """Get all public exams created by a teacher"""
    try:
        exams = db.get_public_exams_by_teacher(teacher_id)
        return jsonify({"success": True, "exams": exams}), 200
    except Exception as e:
        print(f"Error in get_teacher_public_exams: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ==================== GOOGLE OAUTH ENDPOINTS ====================

@app.route("/api/auth/google", methods=["GET"])
def google_auth():
    """Initiate Google OAuth flow"""
    try:
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            return jsonify({
                "success": False,
                "message": "Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
            }), 500
        
        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile"
            ]
        )
        
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="select_account"
        )
        
        # Store state in session for verification
        session["oauth_state"] = state
        
        return jsonify({
            "success": True,
            "authorization_url": authorization_url
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error initiating OAuth: {str(e)}"
        }), 500


@app.route("/api/auth/google/callback", methods=["GET"])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Verify state parameter
        state = request.args.get("state")
        if not state or state != session.get("oauth_state"):
            return jsonify({
                "success": False,
                "message": "Invalid state parameter"
            }), 400
        
        # Check for error in callback
        if "error" in request.args:
            return jsonify({
                "success": False,
                "message": f"OAuth error: {request.args.get('error')}"
            }), 400
        
        # Get authorization code
        code = request.args.get("code")
        if not code:
            return jsonify({
                "success": False,
                "message": "No authorization code received"
            }), 400
        
        # Exchange code for tokens
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile"
            ]
        )
        
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        
        # Get user info from ID token
        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        google_id = id_info.get("sub")
        email = id_info.get("email")
        name = id_info.get("name", email.split("@")[0])
        picture = id_info.get("picture")
        
        # Create or update user in database
        user_result = db.create_or_update_oauth_user(
            email=email,
            username=name,
            google_id=google_id,
            profile_picture=picture
        )
        
        if not user_result["success"]:
            return jsonify(user_result), 500
        
        user = user_result["user"]
        
        # Create session
        session_result = db.create_session(user["_id"])
        
        if not session_result["success"]:
            return jsonify({
                "success": False,
                "message": "Failed to create session"
            }), 500
        
        # Clear OAuth state from session
        session.pop("oauth_state", None)
        
        return jsonify({
            "success": True,
            "message": "Authentication successful",
            "token": session_result["token"],
            "user": user,
            "is_new_user": user_result["is_new"],
            "expires_at": session_result["expires_at"]
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error processing callback: {str(e)}"
        }), 500


@app.route("/api/user/profile", methods=["GET"])
def get_user_profile():
    """Fetch user profile data"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({
                "success": False,
                "message": "Missing or invalid authorization header"
            }), 401
        
        token = auth_header.split(" ")[1]
        
        # Validate session
        user_id = db.validate_session(token)
        
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Invalid or expired token"
            }), 401
        
        # Get user profile
        user = db.get_user_by_id(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        return jsonify({
            "success": True,
            "user": user
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500


if __name__ == "__main__":
    try:
        print("🚀 Starting the student_teacher webside.")
        
        # Debug for auto-reload during development
        app.run(debug=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down the student_teacher webside.")
        print("✅ Cleanup completed. Goodbye!")
    except Exception as e:
        print(f"❌ Error starting application: {e}")