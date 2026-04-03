"""
Authentication Handler
Manages user registration, login, and session management
"""
import bcrypt
from typing import Optional, Dict, Any
from engine.database.mysql_handler import MySQLHandler


class AuthHandler:
    def __init__(self):
        """Initialize authentication handler"""
        self.mysql = MySQLHandler()
    
    # ─── User Registration ───────────────────────────────────────────────
    
    def register_user(self, name: str, email: str, password: str, 
                     country: str = None, language: str = 'en') -> Dict[str, Any]:
        """
        Register a new user
        
        Args:
            name: User's full name
            email: User's email (must be unique)
            password: Plain text password (will be hashed)
            country: User's country
            language: Preferred language (default: 'en')
        
        Returns:
            {
                'success': bool,
                'user_id': str or None,
                'message': str
            }
        """
        # Check if email already exists
        existing_user = self.mysql.get_user_by_email(email)
        if existing_user:
            return {
                'success': False,
                'user_id': None,
                'message': 'Email already registered'
            }
        
        # Hash password
        password_hash = self._hash_password(password)
        
        # Create user
        user_id = self.mysql.create_user(
            name=name,
            email=email,
            password_hash=password_hash,
            country=country,
            language=language
        )
        
        if user_id:
            return {
                'success': True,
                'user_id': user_id,
                'message': 'User registered successfully'
            }
        else:
            return {
                'success': False,
                'user_id': None,
                'message': 'Failed to create user'
            }
    
    # ─── User Login ──────────────────────────────────────────────────────
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user login
        
        Args:
            email: User's email
            password: Plain text password
        
        Returns:
            {
                'success': bool,
                'user_id': str or None,
                'user_data': dict or None,
                'message': str
            }
        """
        # Get user by email
        user = self.mysql.get_user_by_email(email)
        
        if not user:
            return {
                'success': False,
                'user_id': None,
                'user_data': None,
                'message': 'Invalid email or password'
            }
        
        # Check if account is active
        if not user.get('is_active', True):
            return {
                'success': False,
                'user_id': None,
                'user_data': None,
                'message': 'Account is deactivated'
            }
        
        # Verify password
        if not self._verify_password(password, user['password_hash']):
            return {
                'success': False,
                'user_id': None,
                'user_data': None,
                'message': 'Invalid email or password'
            }
        
        # Update last login
        self.mysql.update_last_login(user['user_id'])
        
        # Remove sensitive data before returning
        user_data = {
            'user_id': user['user_id'],
            'name': user['name'],
            'email': user['email'],
            'country': user['country'],
            'language': user['language'],
            'created_at': user['created_at'],
            'last_login': user['last_login']
        }
        
        return {
            'success': True,
            'user_id': user['user_id'],
            'user_data': user_data,
            'message': 'Login successful'
        }
    
    # ─── Password Management ─────────────────────────────────────────────
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    
    def change_password(self, user_id: str, old_password: str, 
                       new_password: str) -> Dict[str, Any]:
        """
        Change user password
        
        Args:
            user_id: User's ID
            old_password: Current password
            new_password: New password
        
        Returns:
            {
                'success': bool,
                'message': str
            }
        """
        # Get user
        cursor = self.mysql.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            return {
                'success': False,
                'message': 'User not found'
            }
        
        # Verify old password
        if not self._verify_password(old_password, user['password_hash']):
            return {
                'success': False,
                'message': 'Current password is incorrect'
            }
        
        # Hash new password
        new_hash = self._hash_password(new_password)
        
        # Update password
        cursor = self.mysql.connection.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE user_id = %s",
            (new_hash, user_id)
        )
        self.mysql.connection.commit()
        cursor.close()
        
        return {
            'success': True,
            'message': 'Password changed successfully'
        }
    
    # ─── User Profile Management ─────────────────────────────────────────
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile (without password)"""
        cursor = self.mysql.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, name, email, country, language, created_at, last_login FROM users WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        cursor.close()
        return user
    
    def update_user_profile(self, user_id: str, name: str = None, 
                           country: str = None, language: str = None) -> Dict[str, Any]:
        """
        Update user profile
        
        Args:
            user_id: User's ID
            name: New name (optional)
            country: New country (optional)
            language: New language (optional)
        
        Returns:
            {
                'success': bool,
                'message': str
            }
        """
        updates = []
        values = []
        
        if name:
            updates.append("name = %s")
            values.append(name)
        if country:
            updates.append("country = %s")
            values.append(country)
        if language:
            updates.append("language = %s")
            values.append(language)
        
        if not updates:
            return {
                'success': False,
                'message': 'No fields to update'
            }
        
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s"
        
        cursor = self.mysql.connection.cursor()
        cursor.execute(query, tuple(values))
        self.mysql.connection.commit()
        cursor.close()
        
        return {
            'success': True,
            'message': 'Profile updated successfully'
        }
    
    def deactivate_account(self, user_id: str) -> Dict[str, Any]:
        """Deactivate user account"""
        cursor = self.mysql.connection.cursor()
        cursor.execute(
            "UPDATE users SET is_active = FALSE WHERE user_id = %s",
            (user_id,)
        )
        self.mysql.connection.commit()
        cursor.close()
        
        return {
            'success': True,
            'message': 'Account deactivated'
        }
    
    def close(self):
        """Close database connection"""
        self.mysql.close()
