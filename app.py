#!/usr/bin/env python3
"""
Somewhere Somehow GL Series Quiz Application

A secure, interactive quiz application for fans of the Thai GL series "Somewhere Somehow".
Features encrypted question storage, user scoring, leaderboards, and admin management.
"""

import os
import json
import secrets
import sqlite3
import base64
import random
import csv
import io
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

import streamlit as st
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

load_dotenv()

APP_CONFIG = {
    'title': 'Somewhere Somehow GL Series Quiz 🩷💙',
    'icon': '🩷💙',
    'layout': 'wide',
    'sidebar_state': 'collapsed'
}

DB_CONFIG = {
    'path': 'quiz_data.db',
    'key_file': '.master_key',
    'salt_file': '.salt'
}

QUIZ_CONFIG = {
    'default_question_limit': 15,
    'all_categories_id': 0,
    'kdf_iterations': 100000
}

PERFORMANCE_THRESHOLDS = {
    'outstanding': 90,
    'great': 70,
    'good': 50
}

def configure_streamlit_page() -> None:
    """Configure Streamlit page settings and load external CSS."""
    st.set_page_config(
        page_title=APP_CONFIG['title'],
        page_icon=APP_CONFIG['icon'],
        layout=APP_CONFIG['layout'],
        initial_sidebar_state=APP_CONFIG['sidebar_state']
    )
    
    try:
        with open('style.css', 'r', encoding='utf-8') as css_file:
            css_content = css_file.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("CSS file not found. Using default styling.")

class SecureQuizManager:
    """Manages quiz data with encryption, database operations, and security features."""
    
    def __init__(self) -> None:
        self.db_path = DB_CONFIG['path']
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
        self.init_database()
    
    def _get_or_create_master_key(self) -> bytes:
        """Generate or retrieve the master encryption key."""
        key_file = DB_CONFIG['key_file']
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as file:
                return file.read()
        
        password = os.environ.get('QUIZ_PASSWORD')
        if not password:
            st.error("QUIZ_PASSWORD environment variable is required but not set. Please set it and restart the application.")
            st.stop()
        
        password_bytes = password.encode('utf-8')
        salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=QUIZ_CONFIG['kdf_iterations'],
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        
        with open(key_file, 'wb') as file:
            file.write(key)
        with open(DB_CONFIG['salt_file'], 'wb') as file:
            file.write(salt)
        
        return key
    
    def encrypt_data(self, data: Dict[str, Any]) -> str:
        """Encrypt data using Fernet symmetric encryption."""
        json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        encrypted_bytes = self.fernet.encrypt(json_data)
        return encrypted_bytes.decode('utf-8')
    
    def decrypt_data(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """Decrypt data using Fernet symmetric encryption."""
        try:
            encrypted_bytes = encrypted_data.encode('utf-8')
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_bytes.decode('utf-8'))
        except Exception as error:
            st.error(f"Decryption error: {str(error)}")
            return None
    
    def init_database(self) -> None:
        """Initialize SQLite database with required tables and default data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quiz_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    encrypted_data TEXT NOT NULL,
                    difficulty TEXT DEFAULT 'medium',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES quiz_categories (id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    category_id INTEGER,
                    score INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES quiz_categories (id)
                )
            """)
            
            cursor.execute("SELECT COUNT(*) FROM quiz_categories")
            if cursor.fetchone()[0] == 0:
                self._insert_default_categories(cursor)
            
            conn.commit()
    
    def _insert_default_categories(self, cursor: sqlite3.Cursor) -> None:
        """Insert default quiz categories into the database."""
        default_categories = [
            ("Character Knowledge", "Think you could write their autobiography? 📝"),
            ("Romance & Relationships", "Relive the sparks, drama, and heart-flutters 💕"),
            ("Quotes & Dialogues", "Because some words live rent-free in your head 💬"),
            ("World & Setting", "From hidden details to iconic backdrops ⛩️")
        ]
        
        for name, description in default_categories:
            cursor.execute(
                "INSERT INTO quiz_categories (name, description) VALUES (?, ?)",
                (name, description)
            )
    
    def get_categories(self) -> List[Tuple[int, str, str]]:
        """Retrieve all quiz categories from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, description FROM quiz_categories ORDER BY name"
            )
            return cursor.fetchall()
    
    def get_questions_by_category(self, category_id: int, limit: int = None) -> List[Dict[str, Any]]:
        """Retrieve and decrypt questions for a specific category."""
        if limit is None:
            limit = QUIZ_CONFIG['default_question_limit']
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, encrypted_data FROM questions WHERE category_id = ? "
                "ORDER BY RANDOM() LIMIT ?",
                (category_id, limit)
            )
            encrypted_questions = cursor.fetchall()
        
        questions = []
        for question_id, encrypted_data in encrypted_questions:
            decrypted_data = self.decrypt_data(encrypted_data)
            if decrypted_data:
                decrypted_data['id'] = question_id
                questions.append(decrypted_data)
        
        return questions
    
    def get_all_questions(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve all questions, optionally filtered by category."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if category_id:
                cursor.execute(
                    "SELECT id, encrypted_data FROM questions WHERE category_id = ? ORDER BY id",
                    (category_id,)
                )
            else:
                cursor.execute("SELECT id, encrypted_data FROM questions ORDER BY id")
            
            encrypted_questions = cursor.fetchall()
        
        questions = []
        for question_id, encrypted_data in encrypted_questions:
            decrypted_data = self.decrypt_data(encrypted_data)
            if decrypted_data:
                decrypted_data['id'] = question_id
                questions.append(decrypted_data)
        
        return questions
    
    def add_question(self, category_id: int, question: str, options: List[str], 
                    correct_answer: int, explanation: str = "") -> None:
        """Add a new encrypted question to the database."""
        question_data = {
            "category_id": category_id,
            "question": question,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation
        }
        
        encrypted_data = self.encrypt_data(question_data)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO questions (category_id, encrypted_data) VALUES (?, ?)",
                (category_id, encrypted_data)
            )
            conn.commit()
    
    def update_question(self, question_id: int, category_id: int, question: str, options: List[str], correct_answer: int, explanation: str = "") -> None:
        """Update an existing question in the database."""
        question_data = {
            "category_id": category_id,
            "question": question,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation
        }
        
        encrypted_data = self.encrypt_data(question_data)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE questions SET category_id = ?, encrypted_data = ? WHERE id = ?",
                (category_id, encrypted_data, question_id)
            )
            conn.commit()
    
    def delete_question(self, question_id: int) -> None:
        """Delete a question from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()
    
    def save_score(self, username: str, category_id: Optional[int], score: int, total_questions: int) -> None:
        """Save a user's quiz score to the database."""
        db_category_id = QUIZ_CONFIG['all_categories_id'] if category_id is None else category_id
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_scores (username, category_id, score, total_questions) "
                "VALUES (?, ?, ?, ?)",
                (username, db_category_id, score, total_questions)
            )
            conn.commit()
    
    def get_leaderboard(self, category_id: Optional[int] = None, limit: int = 20) -> List[Tuple]:
        """Retrieve top scores for leaderboard display."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if category_id is not None:
                cursor.execute("""
                    SELECT username, score, total_questions, 
                           ROUND((score * 100.0 / total_questions), 1) as percentage, completed_at
                    FROM user_scores 
                    WHERE category_id = ?
                    ORDER BY percentage DESC, completed_at ASC 
                    LIMIT ?
                """, (category_id, limit))
            else:
                cursor.execute("""
                    SELECT username, 
                           AVG(score * 100.0 / total_questions) as avg_percentage, COUNT(*) as quizzes_taken, MAX(completed_at) as last_quiz
                    FROM user_scores 
                    GROUP BY username
                    ORDER BY avg_percentage DESC, last_quiz ASC
                    LIMIT ?
                """, (limit,))
            
            return cursor.fetchall()
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Retrieve comprehensive database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.name, COUNT(q.id) as question_count
                FROM quiz_categories c
                LEFT JOIN questions q ON c.id = q.category_id
                GROUP BY c.id, c.name
                ORDER BY c.name
            """)
            category_stats = cursor.fetchall()
            
            cursor.execute("SELECT COUNT(*) FROM user_scores")
            total_scores = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT username) FROM user_scores")
            unique_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(score * 100.0 / total_questions) FROM user_scores")
            avg_score_result = cursor.fetchone()[0]
            avg_score = round(avg_score_result, 1) if avg_score_result else 0
            
            return {
                'category_stats': category_stats,
                'total_scores': total_scores,
                'unique_users': unique_users,
                'avg_score': avg_score,
                'total_questions': sum(count for _, count in category_stats)
            }
    
    def export_questions_to_csv(self) -> str:
        """Export all questions to CSV format."""
        questions = self.get_all_questions()
        categories = self.get_categories()
        category_map = {cat_id: name for cat_id, name, _ in categories}
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Category', 'Question', 'Option A', 'Option B', 'Option C', 'Option D', 
            'Correct Answer', 'Explanation'
        ])
        
        # Write questions
        for q in questions:
            category_name = category_map.get(q['category_id'], 'Unknown')
            correct_letter = chr(64 + q['correct_answer'])  # Convert 1-based to A,B,C,D
            
            writer.writerow([
                category_name,
                q['question'],
                q['options'][0],
                q['options'][1], 
                q['options'][2],
                q['options'][3],
                correct_letter,
                q.get('explanation', '')
            ])
        
        return output.getvalue()
    
    def export_leaderboard_to_csv(self) -> str:
        """Export all user scores to CSV format."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT us.username, c.name as category, us.score, us.total_questions,
                       ROUND((us.score * 100.0 / us.total_questions), 1) as percentage, us.completed_at
                FROM user_scores us
                LEFT JOIN quiz_categories c ON us.category_id = c.id
                ORDER BY us.completed_at DESC
            """)
            scores = cursor.fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Username', 'Category', 'Score', 'Total Questions', 'Percentage', 'Completed At'
        ])
        
        # Write scores
        for username, category, score, total, percentage, completed_at in scores:
            category_name = category if category else 'All Categories'
            writer.writerow([
                username, category_name, score, total, f"{percentage}%", completed_at
            ])
        
        return output.getvalue()
    
    def import_leaderboard_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """Import user scores from CSV content."""
        try:
            # Parse CSV
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            # Get existing categories
            categories = self.get_categories()
            category_map = {name: cat_id for cat_id, name, _ in categories}
            category_map['All Categories'] = QUIZ_CONFIG['all_categories_id']
            
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                try:
                    # Validate required fields
                    required_fields = ['Username', 'Category', 'Score', 'Total Questions']
                    
                    for field in required_fields:
                        if not row.get(field, '').strip():
                            errors.append(f"Row {row_num}: Missing {field}")
                            continue
                    
                    if errors and errors[-1].startswith(f"Row {row_num}"):
                        continue
                    
                    # Parse data
                    username = row['Username'].strip()
                    category_name = row['Category'].strip()
                    score = int(row['Score'].strip())
                    total_questions = int(row['Total Questions'].strip())
                    
                    # Validate score range
                    if score < 0 or score > total_questions:
                        errors.append(f"Row {row_num}: Invalid score {score}/{total_questions}")
                        continue
                    
                    # Get category ID
                    category_id = category_map.get(category_name)
                    if category_id is None:
                        errors.append(f"Row {row_num}: Unknown category '{category_name}'")
                        continue
                    
                    # Insert score
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        
                        # Check if we have a completed_at timestamp
                        completed_at = row.get('Completed At', '').strip()
                        if completed_at:
                            cursor.execute(
                                "INSERT INTO user_scores (username, category_id, score, total_questions, completed_at) "
                                "VALUES (?, ?, ?, ?, ?)",
                                (username, category_id, score, total_questions, completed_at)
                            )
                        else:
                            cursor.execute(
                                "INSERT INTO user_scores (username, category_id, score, total_questions) "
                                "VALUES (?, ?, ?, ?)",
                                (username, category_id, score, total_questions)
                            )
                        
                        conn.commit()
                        imported_count += 1
                        
                except ValueError as e:
                    errors.append(f"Row {row_num}: Invalid number format - {str(e)}")
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return {
                'success': True,
                'imported_count': imported_count,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'imported_count': 0,
                'errors': [f"Failed to parse CSV: {str(e)}"]
            }
    
    def import_questions_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """Import questions from CSV content."""
        try:
            # Parse CSV
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            # Get existing categories
            categories = self.get_categories()
            category_map = {name: cat_id for cat_id, name, _ in categories}
            
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                try:
                    # Validate required fields
                    required_fields = ['Category', 'Question', 'Option A', 'Option B', 'Option C', 'Option D', 'Correct Answer']
                    
                    for field in required_fields:
                        if not row.get(field, '').strip():
                            errors.append(f"Row {row_num}: Missing {field}")
                            continue
                    
                    if errors and errors[-1].startswith(f"Row {row_num}"):
                        continue
                    
                    # Get or create category
                    category_name = row['Category'].strip()
                    if category_name not in category_map:
                        # Create new category
                        with sqlite3.connect(self.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO quiz_categories (name, description) VALUES (?, ?)",
                                (category_name, f"Imported category: {category_name}")
                            )
                            category_id = cursor.lastrowid
                            category_map[category_name] = category_id
                    else:
                        category_id = category_map[category_name]
                    
                    # Validate correct answer
                    correct_answer = row['Correct Answer'].strip().upper()
                    if correct_answer not in ['A', 'B', 'C', 'D']:
                        errors.append(f"Row {row_num}: Invalid correct answer '{correct_answer}'. Must be A, B, C, or D")
                        continue
                    
                    # Convert to 1-based index
                    correct_idx = ord(correct_answer) - ord('A') + 1
                    
                    # Prepare options
                    options = [
                        row['Option A'].strip(),
                        row['Option B'].strip(), 
                        row['Option C'].strip(),
                        row['Option D'].strip()
                    ]
                    
                    # Add question
                    self.add_question(
                        category_id,
                        row['Question'].strip(),
                        options,
                        correct_idx,
                        row.get('Explanation', '').strip()
                    )
                    
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return {
                'success': True,
                'imported_count': imported_count,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to parse CSV: {str(e)}",
                'imported_count': 0,
                'errors': []
            }

@st.cache_resource
def get_quiz_manager() -> SecureQuizManager:
    """Get or create a cached instance of the SecureQuizManager."""
    return SecureQuizManager()

def initialize_session_state() -> None:
    """Initialize Streamlit session state variables with default values."""
    session_defaults = {
        'current_quiz': None,
        'current_question': 0,
        'score': 0,
        'answers': [],
        'quiz_completed': False,
        'username': "",
        'show_admin': False
    }
    
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def reset_quiz_state() -> None:
    """
    Reset quiz-related session state variables to their default values.
    
    This function is called when starting a new quiz or returning to
    the category selection screen.
    """
    st.session_state.current_quiz = None
    st.session_state.current_question = 0
    st.session_state.score = 0
    st.session_state.answers = []
    st.session_state.quiz_completed = False

# ============================================================================
# UI HELPER FUNCTIONS
# ============================================================================

def render_floating_hearts() -> None:
    """
    Render animated floating hearts background using CSS.
    
    Creates a decorative animated background with heart emojis
    floating across the screen at different speeds and positions.
    """
    hearts_html = """
        <div class="floating-hearts">
            <div class="heart heart-pos-10">💕</div>
            <div class="heart heart-pos-20">💖</div>
            <div class="heart heart-pos-30">💝</div>
            <div class="heart heart-pos-40">💗</div>
            <div class="heart heart-pos-50">💓</div>
            <div class="heart heart-pos-60">💕</div>
            <div class="heart heart-pos-70">💖</div>
            <div class="heart heart-pos-80">💝</div>
            <div class="heart heart-pos-90">💗</div>
        </div>
    """
    st.markdown(hearts_html, unsafe_allow_html=True)

def render_section_header(title: str, subtitle: str, icon: str = "") -> None:
    """Render a reusable section header with title and subtitle."""
    header_html = f"""
        <div class="main-header section-header">
            <div class="main-title section-title">{icon} {title}</div>
            <div class="subtitle section-subtitle">{subtitle}</div>
        </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

def render_html_wrapper(css_class: str, content_func=None) -> None:
    """Render HTML wrapper div with optional content function."""
    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
    if content_func:
        content_func()
    # Note: Closing tag should be added manually after content

def render_main_header() -> None:
    """Render the main application header with title and subtitle."""
    header_html = """
        <div class="main-header">
            <h1 class="main-title">
                Somewhere Somehow
            </h1>
            <p class="subtitle">✨ Interactive Quiz ✨</p>
            <p class="tagline">
                "The love story between sharp words and guarded heart awaits...."
            </p>
        </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

def get_performance_message(percentage: float) -> str:
    """Get a performance message based on quiz score percentage."""
    if percentage >= PERFORMANCE_THRESHOLDS['outstanding']:
        return "💙🩷 Outstanding! You're a true Stubborn Dreamer!"
    elif percentage >= PERFORMANCE_THRESHOLDS['great']:
        return "💖 Great job! You know the series very well!"
    elif percentage >= PERFORMANCE_THRESHOLDS['good']:
        return "😊 Good effort! Maybe time for a rewatch?"
    else:
        return "💪 Keep watching and try again! Every fan journey is unique!"

def main() -> None:
    """Main application function that orchestrates the entire quiz application."""
    # Configure Streamlit page settings and load CSS
    configure_streamlit_page()
    
    # Initialize session state variables
    initialize_session_state()
    
    # Render decorative background and main header
    render_floating_hearts()
    render_main_header()
    
    # Create main navigation tabs
    tab_quiz, tab_leaderboard, tab_about, tab_admin = st.tabs([
        "🎯 Take Quiz", 
        "🏆 Leaderboard", 
        "✍🏼 About", 
        "🔧 Admin"
    ])
    
    # Render content for each tab
    with tab_quiz:
        render_quiz_tab()
    
    with tab_leaderboard:
        render_leaderboard_tab()
    
    with tab_about:
        render_about_tab()
    
    with tab_admin:
        render_admin_tab()

# ============================================================================
# TAB RENDERING FUNCTIONS
# ============================================================================

def render_quiz_tab() -> None:
    """
    Render the main quiz-taking interface.
    
    Handles different quiz states:
    1. Username input (if not provided)
    2. Category selection (if no quiz active)
    3. Active quiz questions
    4. Quiz completion and results
    """
    quiz_manager = get_quiz_manager()
    
    # Step 1: Username input
    if not st.session_state.username:
        render_username_input()
        return
    
    # Step 2: Category selection or active quiz
    if st.session_state.current_quiz is None:
        render_category_selection(quiz_manager)
    elif not st.session_state.quiz_completed:
        render_active_quiz(quiz_manager)
    else:
        render_quiz_completion()

def render_username_input() -> None:
    """
    Render the username input interface for new users.
    
    Displays a welcome message and input field for users to enter
    their name before starting the quiz.
    """
    st.markdown(
        '<div class="welcome-message">'
        '🌟 Welcome! Name yourself before Kee\'s sharp tongue meets your quiz score 🤭'
        '</div>', 
        unsafe_allow_html=True
    )
    
    st.markdown('<div class="name-input-section">', unsafe_allow_html=True)
    
    username = st.text_input("Your name", placeholder="Enter your name here...", label_visibility="hidden")
    
    if st.button("Start Your Quiz Adventure! 💫", use_container_width=True):
        if username.strip():
            st.session_state.username = username.strip()
            st.rerun()
        else:
            st.error("Please enter your name to continue!")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_category_selection(quiz_manager: SecureQuizManager) -> None:
    """
    Render the category selection interface.
    
    Args:
        quiz_manager: Instance of SecureQuizManager for data access
    """
    st.markdown(
        f'<div class="welcome-message">'
        f'<h4 style="margin: 0; color: var(--deep-pink); font-family: var(--font-decorative);">'
        f'Hello, {st.session_state.username}! Let\'s start~ </h4>'
        f'</div>', 
        unsafe_allow_html=True
    )

    
    categories = quiz_manager.get_categories()
    category_names = ["All Categories"] + [name for _, name, _ in categories]
    
    # Create tabs for category selection
    tabs = st.tabs(category_names)
    
    # "All Categories" tab
    with tabs[0]:
        render_all_categories_option(quiz_manager, categories)
    
    # Individual category tabs (currently disabled)
    for i, (cat_id, name, description) in enumerate(categories):
        with tabs[i + 1]:
            render_individual_category_option(cat_id, name, description)

def render_all_categories_option(quiz_manager: SecureQuizManager, 
                                categories: List[Tuple[int, str, str]]) -> None:
    """
    Render the "All Categories" quiz option.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
        categories: List of available categories
    """
    st.markdown(
        '<div class="category-header">'
        '<h5 class="category-title">✨ All Categories ✨</h5>'
        '<p class="category-description">Prove you\'re the ultimate fan 🩷💙</p>'
        '</div>', 
        unsafe_allow_html=True
    )
    
    if st.button("Start Quiz with All Categories 💫", key="start_all", use_container_width=True):
        # Collect questions from all categories
        all_questions = []
        for cat_id, _, _ in categories:
            questions = quiz_manager.get_questions_by_category(cat_id)
            all_questions.extend(questions)
        
        if all_questions:
            # Randomize questions and start quiz
            random.shuffle(all_questions)
            reset_quiz_state()
            st.session_state.current_quiz = {
                'category_id': None,
                'category_name': "All Categories",
                'questions': all_questions
            }
            st.rerun()
        else:
            st.error("No questions available!")

def render_individual_category_option(cat_id: int, name: str, description: str) -> None:
    """
    Render an individual category option (currently disabled).
    
    Args:
        cat_id: Category ID
        name: Category name
        description: Category description
    """
    st.markdown(
        f'<div class="category-header">'
        f'<h5 class="category-title">✨ {name} ✨</h5>'
        f'<p class="category-description">{description}</p>'
        f'<p style="color: var(--medium-gray); font-style: italic; margin-top: 1rem;">'
        f'This category is currently unavailable.</p>'
        f'</div>', 
        unsafe_allow_html=True
    )
    st.button(f"Start Quiz with {name}", key=f"cat_{cat_id} 💫", disabled=True, use_container_width=True)

def render_active_quiz(quiz_manager: SecureQuizManager) -> None:
    """
    Render the active quiz interface with questions and answers.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
    """
    quiz = st.session_state.current_quiz
    current_q_idx = st.session_state.current_question
    
    if current_q_idx < len(quiz['questions']):
        question = quiz['questions'][current_q_idx]
        
        # Display progress and question info
        progress = (current_q_idx + 1) / len(quiz['questions'])
        st.progress(progress)
        st.markdown(
            f'<div class="progress-section">'
            f'<strong>Question {current_q_idx + 1} of {len(quiz["questions"])}</strong> • '
            f'Category: <em>{quiz["category_name"]}</em>'
            f'</div>', 
            unsafe_allow_html=True
        )
        
        # Display question
        st.markdown(
            f'<div class="question-card">'
            f'<div class="question-text">{question["question"]}</div>'
            f'</div>', 
            unsafe_allow_html=True
        )
        
        # Display answer options
        render_answer_options(question, quiz_manager)

def render_answer_options(question: Dict[str, Any], quiz_manager: SecureQuizManager) -> None:
    """
    Render answer options and handle answer selection with compact, responsive design.
    
    Args:
        question: Current question data
        quiz_manager: Instance of SecureQuizManager
    """
    # Check if answer has been selected for current question
    current_q_idx = st.session_state.current_question
    answer_selected_key = f"answer_selected_{current_q_idx}"
    
    if answer_selected_key not in st.session_state:
        st.session_state[answer_selected_key] = False
    
    # If answer not yet selected, show answer options
    if not st.session_state[answer_selected_key]:
        

        
        answer_choice = None
        
        # Display answer buttons in a responsive grid layout with consistent styling
        for i, option in enumerate(question['options']):
            button_letter = chr(65 + i)
            button_text = f"{button_letter}. {option}"
            
            # Create clickable styled button using columns for consistent appearance
            if st.button(
                button_text, 
                key=f"ans_{i}",
                use_container_width=True
            ):
                answer_choice = i
        
        # Process answer selection
        if answer_choice is not None:
            process_answer_selection(question, answer_choice, quiz_manager)
            st.session_state[answer_selected_key] = True
            st.rerun()
    
    # If answer has been selected, show all answer options (disabled) and hint below
    else:
        # Display all answer options (disabled state) with selected answer highlighted
        feedback_key = f"feedback_{current_q_idx}"
        feedback = st.session_state.get(feedback_key, {})
        selected_answer = feedback.get('selected_answer')
        
        for i, option in enumerate(question['options']):
            button_letter = chr(65 + i)
            button_text = f"{button_letter}. {option}"
            
            # Use consistent button styling for all options
            if i == selected_answer:
                # Selected answer with gray background to indicate selection
                st.markdown(
                    f'<div style="background-color: #f0f0f0; padding: 0.8rem 1.5rem; border-radius: 12px; margin: 4px 0; border: 2px solid #d0d0d0; text-align: center; font-size: 1rem; font-weight: 300; color: #666; min-height: 3.5rem; display: flex; align-items: center; justify-content: center; font-family: Rubik, sans-serif;">'
                    f'{button_text}'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                # Non-selected answers with same styling as active buttons but disabled appearance
                st.markdown(
                    f'<div style="background-color: #81c3d7; padding: 0.8rem 1.5rem; border-radius: 12px; margin: 4px 0; border: 2px solid #e1e8ff; text-align: center; font-size: 1rem; font-weight: 300; color: #f59eaf; min-height: 3.5rem; display: flex; align-items: center; justify-content: center; font-family: Rubik, sans-serif; opacity: 0.6;">'
                    f'{button_text}'
                    f'</div>',
                    unsafe_allow_html=True
                )
        
        # Add spacing above the hint box
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        
        # Display only the hint/explanation (no correct/incorrect feedback)
        feedback_key = f"feedback_{current_q_idx}"
        if feedback_key in st.session_state:
            feedback = st.session_state[feedback_key]
            if feedback.get('explanation'):
                st.info(f"💡 {feedback['explanation']}")
        
        # Show Next button below the hint
        quiz = st.session_state.current_quiz
        if st.session_state.current_question < len(quiz['questions']) - 1:
            if st.button("➡️ Next Question", key="next_btn", use_container_width=True):
                move_to_next_question(quiz_manager)
        else:
            if st.button("🏁 Finish Quiz", key="finish_btn", use_container_width=True):
                complete_quiz(quiz_manager)

def process_answer_selection(question: Dict[str, Any], answer_choice: int, quiz_manager: SecureQuizManager) -> None:
    """
    Process the user's answer selection and update quiz state.
    
    Args:
        question: Current question data
        answer_choice: Index of selected answer (0-based)
        quiz_manager: Instance of SecureQuizManager
    """
    # Check if answer is correct (convert 1-based to 0-based)
    correct_answer_idx = question['correct_answer'] - 1
    is_correct = answer_choice == correct_answer_idx
    
    # Update score
    if is_correct:
        st.session_state.score += 1
    
    # Store feedback in session state for display
    current_q_idx = st.session_state.current_question
    feedback_key = f"feedback_{current_q_idx}"
    st.session_state[feedback_key] = {
        'is_correct': is_correct,
        'explanation': question.get('explanation'),
        'selected_answer': answer_choice
    }
    
    # Record answer
    st.session_state.answers.append({
        'question': question['question'],
        'selected': answer_choice,
        'correct': question['correct_answer'],
        'is_correct': is_correct
    })

def move_to_next_question(quiz_manager: SecureQuizManager) -> None:
    """
    Move to the next question in the quiz.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
    """
    st.session_state.current_question += 1
    st.rerun()

def complete_quiz(quiz_manager: SecureQuizManager) -> None:
    """
    Complete the quiz and save the score.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
    """
    quiz = st.session_state.current_quiz
    st.session_state.quiz_completed = True
    quiz_manager.save_score(
        st.session_state.username,
        quiz['category_id'],
        st.session_state.score,
        len(quiz['questions'])
    )
    st.rerun()

def render_database_statistics(quiz_manager: SecureQuizManager) -> None:
    """Render database statistics section for admin view."""
    stats = quiz_manager.get_database_statistics()
    categories = quiz_manager.get_categories()
    
    render_section_header("Database Statistics", "Overview of quiz data and user engagement", "🔍")
    
    # Mobile-friendly stats grid
    st.markdown(f"""
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-icon">👥</div>
                <div class="stat-content">
                    <div class="stat-value">{stats['unique_users']}</div>
                    <div class="stat-label">Total Users</div>
                </div>
            </div>
            <div class="stat-item">
                <div class="stat-icon">🎯</div>
                <div class="stat-content">
                    <div class="stat-value">{stats['total_scores']}</div>
                    <div class="stat-label">Quiz Sessions</div>
                </div>
            </div>
            <div class="stat-item">
                <div class="stat-icon">📚</div>
                <div class="stat-content">
                    <div class="stat-value">{len(categories)}</div>
                    <div class="stat-label">Categories</div>
                </div>
            </div>
            <div class="stat-item">
                <div class="stat-icon">⭐</div>
                <div class="stat-content">
                    <div class="stat-value">{stats['avg_score']}%</div>
                    <div class="stat-label">Avg Score</div>
                </div>
            </div>
            <div class="stat-item">
                <div class="stat-icon">📝</div>
                <div class="stat-content">
                    <div class="stat-value">{stats['total_questions']}</div>
                    <div class="stat-label">Questions</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
            
            <div class="questions-breakdown">
                <div class="breakdown-title">
                    📊 Questions per Category
                </div>
    """, unsafe_allow_html=True)
    
    for cat_name, count in stats['category_stats']:
        st.markdown(f"""
                <div class="breakdown-item">
                    <span class="breakdown-category">{cat_name}</span>
                    <span class="breakdown-count">{count}</span>
                </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""            </div>        </div>    """, unsafe_allow_html=True)

def render_quiz_completion() -> None:
    """
    Render the quiz completion screen with results and actions.
    
    Displays the user's final score, performance message, and options
    to take another quiz or return to category selection.
    """
    quiz = st.session_state.current_quiz
    score = st.session_state.score
    total = len(quiz['questions'])
    percentage = round((score / total) * 100, 1)
    
    # Get performance message
    message = get_performance_message(percentage)
    
    # Display score card
    score_card_html = f"""
        <div class="score-card">
            <div class="score-title">Quiz Complete! 🎉</div>
            <div class="score-text">
                <strong>{st.session_state.username}</strong>, you scored<br>
                <span class="score-display">
                    {score}/{total} ({percentage}%)
                </span><br><br>
                <div class="score-message">
                    {message}
                </div>
            </div>
        </div>
    """
    st.markdown(score_card_html, unsafe_allow_html=True)
    
    # Action buttons
    st.markdown("<div class='margin-top-2rem'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="small")
    
    with col1:
        if st.button("🔄 Take Another Quiz", use_container_width=True):
            reset_quiz_state()
            st.rerun()
    
    with col2:
        if st.button("🏠 Back to Categories", use_container_width=True):
            reset_quiz_state()
            st.rerun()

def render_leaderboard_tab() -> None:
    """
    Render the leaderboard tab with top scores across categories.
    
    Displays leaderboards for all categories combined and individual
    category leaderboards in separate tabs.
    """
    quiz_manager = get_quiz_manager()
    
    # Header
    render_section_header("Leaderboard", "See how you rank among other fans!", "🏆")
    
    categories = quiz_manager.get_categories()
    category_options = ["All Categories"] + [name for _, name, _ in categories]
    
    # Create leaderboard tabs
    tabs = st.tabs(category_options)
    
    # All Categories leaderboard
    with tabs[0]:
        render_overall_leaderboard(quiz_manager)
    
    # Individual category leaderboards
    for i, (cat_id, name, _) in enumerate(categories):
        with tabs[i + 1]:
            render_category_leaderboard(quiz_manager, cat_id, name)

def render_overall_leaderboard(quiz_manager: SecureQuizManager) -> None:
    """
    Render the overall leaderboard across all categories.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
    """
    scores = quiz_manager.get_leaderboard()
    
    if scores:
        st.markdown("""
            <div class="leaderboard-container">
                <div class="leaderboard-title">🌟 Top Players (All Categories)</div>
        """, unsafe_allow_html=True)
        
        for i, (username, avg_percentage, quizzes_taken, last_quiz) in enumerate(scores):
            emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "⭐"
            rank_class = f"rank-{i + 1}" if i < 3 else ""
            
            player_card_html = f"""
                <div class="player-card {rank_class}">
                    <div class="player-info">
                        <div class="player-name">
                            <span class="player-rank">{emoji}</span>
                            {username}
                        </div>
                        <div class="player-stats">
                            <div class="player-percentage">{avg_percentage:.1f}%</div>
                            <div class="player-details">{quizzes_taken} quizzes taken</div>
                        </div>
                    </div>
                </div>
            """
            st.markdown(player_card_html, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        render_no_scores_message("Take a quiz to see your name here!")

def render_category_leaderboard(quiz_manager: SecureQuizManager, cat_id: int, name: str) -> None:
    """
    Render leaderboard for a specific category.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
        cat_id: Category ID
        name: Category name
    """
    scores = quiz_manager.get_leaderboard(cat_id)
    
    if scores:
        st.markdown(f"""
            <div class="leaderboard-container">
                <div class="leaderboard-title">🎯 Top Scores - {name}</div>
        """, unsafe_allow_html=True)
        
        for j, (username, score, total, percentage, completed_at) in enumerate(scores):
            emoji = "🥇" if j == 0 else "🥈" if j == 1 else "🥉" if j == 2 else "⭐"
            rank_class = f"rank-{j + 1}" if j < 3 else ""
            
            player_card_html = f"""
                <div class="player-card {rank_class}">
                    <div class="player-info">
                        <div class="player-name">
                            <span class="player-rank">{emoji}</span>
                            {username}
                        </div>
                        <div class="player-stats">
                            <div class="player-percentage">{percentage}%</div>
                            <div class="player-details">{score}/{total} correct on {completed_at[:10]}</div>
                        </div>
                    </div>
                </div>
            """
            st.markdown(player_card_html, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        render_no_scores_message(f"No scores yet for {name}. Be the first to take the quiz!")

def render_no_scores_message(message: str) -> None:
    """
    Render a "no scores" message for empty leaderboards.
    
    Args:
        message: Custom message to display
    """
    no_scores_html = f"""
        <div class="no-scores-message">
            <span class="no-scores-emoji">🎯</span>
            {message}
        </div>
    """
    st.markdown(no_scores_html, unsafe_allow_html=True)

def render_about_tab() -> None:
    """
    Render the about tab with information about the series and quiz.
    
    Provides comprehensive information about:
    - The quiz application features
    - The "Somewhere Somehow" series
    - How to play and get high scores
    """
    # Header
    render_section_header("About", "Learn more about Somewhere Somehow Quiz", "✍🏼")
    
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # Add series image
    st.image("image/swsh.png", caption="Somewhere Somehow GL Series", use_container_width=True)
    
    st.markdown('<div class="name-input-section">', unsafe_allow_html=True)
    
    # About content
    about_content = """
    Welcome to the interactive quiz experience for **Somewhere Somehow GL**, the romantic comedy series 
    that captured hearts with its tale of true love, comedy and second chances!
    
    #### 🌟 Features:
    - **Multiple Categories**: Test your knowledge across different aspects of the series.
    - **Competitive Fun**: Compare your scores with other fans on the leaderboard.
    - **Encouragement to Rewatch**: Get hints and reminders to rewatch key episodes for better understanding.

    #### 💕 About the Series:
    *Somewhere Somehow* follows Kee, a reserved, witty, emotionally distant, and eco-conscious protagonist, alongside Peem, an affluent and admired high school sweetheart. Their worlds meet in a sequence of seemingly random encounters. Sickeningly sweet and adorable interactions follow suit, with a touch of humorous events. Even then, every love story has its own misunderstandings and struggles.  

    Watch the best romantic comedy Thai GL series, *Somewhere Somehow*, on [Idol Factory YouTube](https://youtube.com/playlist?list=PL4D0KlUVq4Ix1AF1_vliipbSFOvvGUNWO&si=rY-nJ3_0LA59ck0W) every Friday night at 10:30 PM Thailand time.
    
    #### 🎯 Quiz Categories:
    Due to limited amount of questions, only "All Categories" category is available for now.
    - **All Categories**: Prove you\'re the ultimate fan 🩷💙
    - **Character Knowledge**: Think you could write their autobiography? 📝
    - **Romance & Relationships**: Relive the sparks, drama, and heart-flutters 💕
    - **Quotes & Dialogues**: Because some words live rent-free in your head 💬
    - **World & Setting**: From hidden details to iconic backdrops ⛩️
    
    #### 🏆 How to Play:
    1. Enter your name to get started.
    2. Choose "All Categories" quiz category.
    3. Answer questions about the series. Answers use the exact wordings from the official subtitles by Idol Factory.
    4. See your results and compare with others.
    5. Take more quizzes to improve your ranking!
    
    #### 💡 Tips for High Scores:
    - Rewatch episodes on YouTube.
    - Pay attention to character and world setting details.
    - Remember the emotional moments.
    - Notice the little details in dialogue.
    - Pay attention to English subtitles. Answers use the exact wordings from the official subtitles by Idol Factory.
    
    ---
    """
    
    st.markdown(about_content)
    st.markdown("<div style='text-align: center;'>PeemKie for the win!!! 🚀</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_admin_tab() -> None:
    """
    Render the admin tab with authentication and management features.
    
    Provides admin functionality for:
    - Question management (add, edit, delete)
    - Database statistics viewing
    - Content administration
    """
    # Header
    render_section_header("Admin", "Manage quiz content and view statistics", "🔧")
    
    st.markdown('<div class="name-input-section">', unsafe_allow_html=True)
    
    # Admin authentication
    admin_password = st.text_input("Admin Password:", type="password")
    
    # Get admin password from environment
    correct_admin_password = os.environ.get('ADMIN_PASSWORD')
    if not correct_admin_password:
        st.error("❌ ADMIN_PASSWORD environment variable is not set. Admin access is disabled for security.")
        st.info("Please set the ADMIN_PASSWORD environment variable and restart the application.")
        return
    
    # Verify admin access using constant-time comparison
    if admin_password and secrets.compare_digest(admin_password, correct_admin_password):
        st.success("🔓 Admin access granted!")
        render_admin_interface()
    elif admin_password:
        st.error("❌ Invalid admin password!")
    else:
        st.info("🔒 Enter admin password to access management features.")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_admin_interface() -> None:
    """
    Render the main admin interface with all management features.
    
    Provides sections for:
    - Adding new questions
    - Editing existing questions
    - Database export/import
    - Viewing database statistics
    """
    quiz_manager = get_quiz_manager()
    
    # Add new question section
    render_add_question_section(quiz_manager)
    
    # Edit existing questions section
    render_edit_questions_section(quiz_manager)
    
    # Database export/import section
    render_database_export_import_section(quiz_manager)
    
    # Database statistics section
    render_admin_statistics_section(quiz_manager)

def render_add_question_section(quiz_manager: SecureQuizManager) -> None:
    """
    Render the add new question section of the admin interface.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
    """
    st.markdown("##### ➕ Add New Question")
    
    categories = quiz_manager.get_categories()
    category_options = {name: cat_id for cat_id, name, _ in categories}
    
    # Question input form
    selected_cat = st.selectbox("Select Category:", list(category_options.keys()))
    question_text = st.text_area("Question:", placeholder="Enter your question here...")
    
    option1 = st.text_input("Option A:", placeholder="First option")
    option2 = st.text_input("Option B:", placeholder="Second option")
    option3 = st.text_input("Option C:", placeholder="Third option")
    option4 = st.text_input("Option D:", placeholder="Fourth option")
    
    correct_answer = st.selectbox("Correct Answer:", ["A", "B", "C", "D"])
    explanation = st.text_area("Hint:", placeholder="How to get the correct answer")
    
    # Add question button
    if st.button("🚀 Add Question", use_container_width=True):
        if question_text and option1 and option2 and option3 and option4:
            options = [option1, option2, option3, option4]
            correct_idx = ord(correct_answer) - ord('A') + 1  # Convert to 1-indexed
            
            quiz_manager.add_question(
                category_options[selected_cat],
                question_text,
                options,
                correct_idx,
                explanation
            )
            
            st.markdown(
                '<div class="success-message">✅ Question added successfully!</div>', 
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="error-message">❌ Please fill in all required fields!</div>', 
                unsafe_allow_html=True
            )

def render_edit_questions_section(quiz_manager: SecureQuizManager) -> None:
    """
    Render the edit existing questions section of the admin interface.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
    """
    st.markdown("##### ✏️ Edit Existing Questions")
    
    categories = quiz_manager.get_categories()
    category_options = {name: cat_id for cat_id, name, _ in categories}
    
    # Category filter
    edit_categories = ["All Categories"] + list(category_options.keys())
    selected_edit_cat = st.selectbox(
        "Filter by Category:", 
        edit_categories, 
        key="edit_category"
    )
    
    # Get questions based on selected category
    if selected_edit_cat == "All Categories":
        all_questions = quiz_manager.get_all_questions()
    else:
        all_questions = quiz_manager.get_all_questions(category_options[selected_edit_cat])
    
    if all_questions:
        render_question_editor(quiz_manager, all_questions, category_options)
    else:
        st.info("No questions found for the selected category.")

def render_question_editor(quiz_manager: SecureQuizManager, all_questions: List[Dict[str, Any]], category_options: Dict[str, int]) -> None:
    """
    Render the question editor interface.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
        all_questions: List of all questions to edit
        category_options: Mapping of category names to IDs
    """
    # Create question summaries for selection
    question_summaries = []
    for q in all_questions:
        cat_name = next(
            (name for name, cat_id in category_options.items() if cat_id == q['category_id']), 
            "Unknown"
        )
        summary = (
            f"ID {q['id']}: {q['question'][:50]}"
            f"{'...' if len(q['question']) > 50 else ''} ({cat_name})"
        )
        question_summaries.append(summary)
    
    selected_question_summary = st.selectbox(
        "Select Question to Edit:", 
        question_summaries, 
        key="question_select"
    )
    
    if selected_question_summary:
        # Find the selected question
        selected_id = int(selected_question_summary.split(":")[0].replace("ID ", ""))
        selected_question = next(q for q in all_questions if q['id'] == selected_id)
        
        render_question_edit_form(quiz_manager, selected_question, category_options, selected_id)

def render_question_edit_form(quiz_manager: SecureQuizManager, selected_question: Dict[str, Any], category_options: Dict[str, int], selected_id: int) -> None:
    """
    Render the question edit form.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
        selected_question: The question being edited
        category_options: Mapping of category names to IDs
        selected_id: ID of the selected question
    """
    
    # Edit form fields
    edit_selected_cat = st.selectbox(
        "Category:", 
        list(category_options.keys()),
        index=list(category_options.values()).index(selected_question['category_id']),
        key="edit_cat_select"
    )
    
    edit_question_text = st.text_area(
        "Question:", 
        value=selected_question['question'], 
        key="edit_question"
    )
    
    edit_option1 = st.text_input("Option A:", value=selected_question['options'][0], key="edit_opt1")
    edit_option2 = st.text_input("Option B:", value=selected_question['options'][1], key="edit_opt2")
    edit_option3 = st.text_input("Option C:", value=selected_question['options'][2], key="edit_opt3")
    edit_option4 = st.text_input("Option D:", value=selected_question['options'][3], key="edit_opt4")
    
    # Correct answer selection
    current_correct_idx = selected_question['correct_answer'] - 1
    current_correct_letter = chr(65 + current_correct_idx)
    edit_correct_answer = st.selectbox(
        "Correct Answer:", 
        ["A", "B", "C", "D"], 
        index=["A", "B", "C", "D"].index(current_correct_letter), 
        key="edit_correct"
    )
    
    edit_explanation = st.text_area(
        "Hint:", 
        value=selected_question.get('explanation', ''), 
        key="edit_explanation"
    )
    
    # Action buttons
    render_question_action_buttons(quiz_manager, edit_selected_cat, edit_question_text, edit_option1, edit_option2, edit_option3, edit_option4, edit_correct_answer, edit_explanation, category_options, selected_id)

def render_question_action_buttons(quiz_manager: SecureQuizManager, edit_selected_cat: str, edit_question_text: str, edit_option1: str, edit_option2: str, edit_option3: str, edit_option4: str, edit_correct_answer: str, edit_explanation: str, category_options: Dict[str, int], selected_id: int) -> None:
    """
    Render action buttons for question editing.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
        edit_selected_cat: Selected category name
        edit_question_text: Question text
        edit_option1-4: Answer options
        edit_correct_answer: Correct answer letter
        edit_explanation: Question explanation
        category_options: Category name to ID mapping
        selected_id: ID of question being edited
    """
    if st.button("💾 Update Question", key="update_btn", use_container_width=True):
        if edit_question_text and edit_option1 and edit_option2 and edit_option3 and edit_option4:
            edit_options = [edit_option1, edit_option2, edit_option3, edit_option4]
            edit_correct_idx = ord(edit_correct_answer) - ord('A') + 1  # Convert to 1-indexed
            
            quiz_manager.update_question(
                selected_id,
                category_options[edit_selected_cat],
                edit_question_text,
                edit_options,
                edit_correct_idx,
                edit_explanation
            )
            
            st.markdown(
                '<div class="success-message">✅ Question updated successfully!</div>', 
                unsafe_allow_html=True
            )
            st.rerun()
        else:
            st.markdown(
                '<div class="error-message">❌ Please fill in all required fields!</div>', 
                unsafe_allow_html=True
            )
    
    if st.button("🗑️ Delete Question", key="delete_btn", use_container_width=True):
        quiz_manager.delete_question(selected_id)
        st.markdown(
            '<div class="success-message">✅ Question deleted successfully!</div>', 
            unsafe_allow_html=True
        )
        st.rerun()

def render_database_export_import_section(quiz_manager: SecureQuizManager) -> None:
    """
    Render the database export/import section of the admin interface.
    
    Args:
        quiz_manager: Instance of SecureQuizManager
    """
    st.markdown("##### 📁 Database Export/Import")
    
    # Create tabs for Questions and Leaderboard
    tab1, tab2 = st.tabs(["📝 Questions", "🏆 Leaderboard"])
    
    with tab1:
        # Create two columns for export and import
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📤 Export Questions**")
            st.markdown("Download all questions as a CSV file for backup or sharing.")
            
            if st.button("📥 Export Questions to CSV", use_container_width=True, key="export_questions_btn"):
                try:
                    csv_data = quiz_manager.export_questions_to_csv()
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"quiz_questions_export_{timestamp}.csv"
                    
                    st.download_button(
                        label="💾 Download Questions CSV",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    st.markdown(
                        '<div class="success-message">✅ Export ready! Click the download button above.</div>',
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.markdown(
                        f'<div class="error-message">❌ Export failed: {str(e)}</div>',
                        unsafe_allow_html=True
                    )
        
        with col2:
            st.markdown("**📤 Import Questions**")
            st.markdown("Upload a CSV file to import questions. New categories will be created automatically.")
            
            # File uploader
            uploaded_questions_file = st.file_uploader(
                "Choose Questions CSV file",
                type="csv",
                key="questions_csv_upload",
                help="CSV should have columns: Category, Question, Option A, Option B, Option C, Option D, Correct Answer, Explanation"
            )
            
            if uploaded_questions_file is not None:
                if st.button("📤 Import Questions", use_container_width=True, key="import_questions_btn"):
                    try:
                        # Read the uploaded file
                        csv_content = uploaded_questions_file.read().decode('utf-8')
                        
                        # Import questions
                        result = quiz_manager.import_questions_from_csv(csv_content)
                        
                        if result['success']:
                            st.markdown(
                                f'<div class="success-message">✅ Successfully imported {result["imported_count"]} questions!</div>',
                                unsafe_allow_html=True
                            )
                            
                            if result['errors']:
                                st.markdown("**⚠️ Some rows had errors:**")
                                for error in result['errors'][:10]:  # Show first 10 errors
                                    st.markdown(f"- {error}")
                                if len(result['errors']) > 10:
                                    st.markdown(f"... and {len(result['errors']) - 10} more errors")
                            
                            # Clear the cache to refresh data
                            st.cache_resource.clear()
                            st.rerun()
                        else:
                            st.markdown(
                                f'<div class="error-message">❌ Import failed: {result["error"]}</div>',
                                unsafe_allow_html=True
                            )
                            
                    except Exception as e:
                        st.markdown(
                            f'<div class="error-message">❌ Import failed: {str(e)}</div>',
                            unsafe_allow_html=True
                        )
    
    with tab2:
        # Create two columns for export and import
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📤 Export Leaderboard**")
            st.markdown("Download all user scores as a CSV file for backup or analysis.")
            
            if st.button("📥 Export Leaderboard to CSV", use_container_width=True, key="export_leaderboard_btn"):
                try:
                    csv_data = quiz_manager.export_leaderboard_to_csv()
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"quiz_leaderboard_export_{timestamp}.csv"
                    
                    st.download_button(
                        label="💾 Download Leaderboard CSV",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    st.markdown(
                        '<div class="success-message">✅ Export ready! Click the download button above.</div>',
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.markdown(
                        f'<div class="error-message">❌ Export failed: {str(e)}</div>',
                        unsafe_allow_html=True
                    )
        
        with col2:
            st.markdown("**📤 Import Leaderboard**")
            st.markdown("Upload a CSV file to import user scores. Categories must already exist.")
            
            # File uploader
            uploaded_leaderboard_file = st.file_uploader(
                "Choose Leaderboard CSV file",
                type="csv",
                key="leaderboard_csv_upload",
                help="CSV should have columns: Username, Category, Score, Total Questions, Percentage, Completed At"
            )
            
            if uploaded_leaderboard_file is not None:
                if st.button("📤 Import Leaderboard", use_container_width=True, key="import_leaderboard_btn"):
                    try:
                        # Read the uploaded file
                        csv_content = uploaded_leaderboard_file.read().decode('utf-8')
                        
                        # Import leaderboard
                        result = quiz_manager.import_leaderboard_from_csv(csv_content)
                        
                        if result['success']:
                            st.markdown(
                                f'<div class="success-message">✅ Successfully imported {result["imported_count"]} scores!</div>',
                                unsafe_allow_html=True
                            )
                            
                            if result['errors']:
                                st.markdown("**⚠️ Some rows had errors:**")
                                for error in result['errors'][:10]:  # Show first 10 errors
                                    st.markdown(f"- {error}")
                                if len(result['errors']) > 10:
                                    st.markdown(f"... and {len(result['errors']) - 10} more errors")
                            
                            # Clear the cache to refresh data
                            st.cache_resource.clear()
                            st.rerun()
                        else:
                            st.markdown(
                                f'<div class="error-message">❌ Import failed: {result["errors"][0] if result["errors"] else "Unknown error"}</div>',
                                unsafe_allow_html=True
                            )
                            
                    except Exception as e:
                        st.markdown(
                            f'<div class="error-message">❌ Import failed: {str(e)}</div>',
                            unsafe_allow_html=True
                        )
    
    # CSV format help
    with st.expander("📋 CSV Format Help"):
        format_tab1, format_tab2 = st.tabs(["📝 Questions Format", "🏆 Leaderboard Format"])
        
        with format_tab1:
            st.markdown("""
            **Required Questions CSV Format:**
            
            Your CSV file should have the following columns (in this exact order):
            
            | Column | Description | Example |
            |--------|-------------|----------|
            | Category | Question category | "Character Knowledge" |
            | Question | The question text | "What is the main character's name?" |
            | Option A | First answer option | "Alice" |
            | Option B | Second answer option | "Bob" |
            | Option C | Third answer option | "Charlie" |
            | Option D | Fourth answer option | "Diana" |
            | Correct Answer | Correct option (A, B, C, or D) | "A" |
            | Explanation | Optional hint/explanation | "Alice is the protagonist" |
            
            **Notes:**
            - The first row should contain column headers
            - Categories will be created automatically if they don't exist
            - Correct Answer must be exactly A, B, C, or D
            - Explanation column is optional
            - All other columns are required
            """)
        
        with format_tab2:
            st.markdown("""
            **Required Leaderboard CSV Format:**
            
            Your CSV file should have the following columns (in this exact order):
            
            | Column | Description | Example |
            |--------|-------------|----------|
            | Username | Player's username | "Alice123" |
            | Category | Quiz category name | "Character Knowledge" or "All Categories" |
            | Score | Number of correct answers | "8" |
            | Total Questions | Total number of questions | "10" |
            | Percentage | Score percentage (optional) | "80.0%" |
            | Completed At | Timestamp (optional) | "2024-01-15 14:30:25" |
            
            **Notes:**
            - The first row should contain column headers
            - Categories must already exist (except "All Categories")
            - Score must be between 0 and Total Questions
            - Percentage column is calculated automatically if not provided
            - Completed At column is optional (uses current time if not provided)
            - Username, Category, Score, and Total Questions are required
            """)

def render_admin_statistics_section(quiz_manager: SecureQuizManager) -> None:
    """Render the admin statistics section."""
    render_database_statistics(quiz_manager)

if __name__ == "__main__":
    main()
