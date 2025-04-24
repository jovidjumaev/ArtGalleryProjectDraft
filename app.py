import sys
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from db import get_connection
import oracledb
import re
from datetime import datetime
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

def create_users_table():
    """Create the users table if it doesn't exist"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if sequence exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM user_sequences 
            WHERE sequence_name = 'USER_ID_SEQ'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                CREATE SEQUENCE user_id_seq
                START WITH 1
                INCREMENT BY 1
                NOCACHE
                NOCYCLE
            """)
        
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM user_tables 
            WHERE table_name = 'USERS'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                CREATE TABLE users (
                    user_id NUMBER DEFAULT user_id_seq.NEXTVAL PRIMARY KEY,
                    username VARCHAR2(20) UNIQUE NOT NULL,
                    password_hash VARCHAR2(255) NOT NULL,
                    email VARCHAR2(255) UNIQUE NOT NULL,
                    first_name VARCHAR2(30) NOT NULL,
                    last_name VARCHAR2(30) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX idx_users_username ON users(username)
            """)
            
            cursor.execute("""
                CREATE INDEX idx_users_email ON users(email)
            """)
            
            conn.commit()
            print("Users table created successfully")
    except Exception as e:
        print(f"Error creating users table: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Create users table when app starts
create_users_table()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check if user exists and password is correct
            cursor.execute("""
                SELECT user_id, password_hash, first_name, last_name 
                FROM users 
                WHERE username = :username
            """, username=username)
            
            user = cursor.fetchone()
            
            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['user_name'] = f"{user[2]} {user[3]}"
                session['logged_in'] = True
                
                # Update last login time
                cursor.execute("""
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP 
                    WHERE user_id = :user_id
                """, user_id=user[0])
                conn.commit()
                
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Invalid username or password')
            
        except Exception as e:
            print(f"Login error: {str(e)}")
            return render_template('login.html', error='An error occurred during login')
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.form['firstName']
            last_name = request.form['lastName']
            email = request.form['email']
            username = request.form['username']
            password = request.form['password']
            confirm_password = request.form['confirmPassword']
            
            # Print form data for debugging (excluding password)
            print("\n=== Signup Debug Information ===")
            print("Form data received:")
            print(f"First Name: {first_name}")
            print(f"Last Name: {last_name}")
            print(f"Email: {email}")
            print(f"Username: {username}")
            
            if password != confirm_password:
                return render_template('signup.html', error='Passwords do not match')
            
            # Validate password requirements
            if len(password) < 8:
                return render_template('signup.html', error='Password must be at least 8 characters long')
            if not any(c.isalpha() for c in password):
                return render_template('signup.html', error='Password must contain at least one letter')
            if not any(c.isdigit() for c in password):
                return render_template('signup.html', error='Password must contain at least one number')
            
            print("\nAttempting database connection...")
            conn = get_connection()
            print("Database connection successful")
            
            cursor = conn.cursor()
            print("Cursor created successfully")
            
            # Check if username already exists
            print("\nChecking for existing username...")
            cursor.execute("SELECT 1 FROM users WHERE username = :username", username=username)
            if cursor.fetchone():
                return render_template('signup.html', error='Username already exists')
            
            # Check if email already exists
            print("Checking for existing email...")
            cursor.execute("SELECT 1 FROM users WHERE email = :email", email=email)
            if cursor.fetchone():
                return render_template('signup.html', error='Email already registered')
            
            # Create new user
            print("\nGenerating password hash...")
            password_hash = generate_password_hash(password)
            
            print("Attempting to insert new user into database...")
            
            insert_query = """
                INSERT INTO users (username, password_hash, email, first_name, last_name)
                VALUES (:username, :password_hash, :email, :first_name, :last_name)
                RETURNING user_id INTO :user_id
            """
            
            user_id_var = cursor.var(int)
            
            print("Executing insert query...")
            cursor.execute(insert_query, {
                'username': username,
                'password_hash': password_hash,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'user_id': user_id_var
            })
            
            # Commit the transaction
            conn.commit()
            
            # Get the new user's ID
            user_id = user_id_var.getvalue()[0]
            
            # Set up the session
            session['user_id'] = user_id
            session['user_name'] = f"{first_name} {last_name}"
            session['logged_in'] = True
            
            print("User created successfully!")
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Signup error: {str(e)}")
            return render_template('signup.html', error='An error occurred during signup')
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/add_artist', methods=['GET', 'POST'])
@login_required
def add_artist():
    if request.method == 'POST':
        # Initialize connection variables
        conn = None
        cur = None
        
        try:
            # Get form data and print for debugging
            print("Received form data:", request.form)
            
            # Handle medium with "Other" option
            usual_medium = request.form.get('usualMedium', '').strip()
            if usual_medium == 'other':
                usual_medium = request.form.get('otherMediumInput', '').strip()
            
            # Handle style with "Other" option
            usual_style = request.form.get('usualStyle', '').strip()
            if usual_style == 'other':
                usual_style = request.form.get('otherStyleInput', '').strip()
            
            # Handle type with "Other" option
            usual_type = request.form.get('usualType', '').strip()
            if usual_type == 'other':
                usual_type = request.form.get('otherTypeInput', '').strip()

            # Validate field lengths
            if len(usual_medium) > 30:
                return render_template('add_artist.html', error="❌ Medium field exceeds 30 characters. Please shorten it.")
            if len(usual_style) > 30:
                return render_template('add_artist.html', error="❌ Style field exceeds 30 characters. Please shorten it.")
            if len(usual_type) > 30:
                return render_template('add_artist.html', error="❌ Type field exceeds 30 characters. Please shorten it.")

            # Get all required fields
            data = {
                'interviewDate': request.form.get('interviewDate', '').strip(),
                'interviewerName': request.form.get('interviewerName', '').strip(),
                'firstName': request.form.get('firstName', '').strip(),
                'lastName': request.form.get('lastName', '').strip(),
                'street': request.form.get('street', '').strip(),
                'zip': request.form.get('zip', '').strip(),
                'areaCode': request.form.get('areaCode', '').strip(),
                'telephoneNumber': request.form.get('telephoneNumber', '').strip(),
                'socialSecurityNumber': request.form.get('socialSecurityNumber', '').strip(),
                'usualMedium': usual_medium,
                'usualStyle': usual_style,
                'usualType': usual_type,
                'salesLastYear': 0,  # Default values for new artists
                'salesYearToDate': 0
            }

            # Print collected data for debugging
            print("Processed data:", data)
            
            # Print which fields are empty
            empty_fields = [field for field, value in data.items() if not value and field not in ['salesLastYear', 'salesYearToDate']]
            if empty_fields:
                print("Empty fields:", empty_fields)

            # Validate required fields
            required_fields = ['interviewDate', 'interviewerName', 'firstName', 
                             'lastName', 'street', 'zip', 'areaCode',
                             'telephoneNumber', 'socialSecurityNumber', 'usualMedium',
                             'usualStyle', 'usualType']
            
            missing_fields = [field for field in required_fields if not data[field]]
            if missing_fields:
                print("Missing fields:", missing_fields)  # Debug print
                return render_template('add_artist.html', error=f"❌ The following required fields are missing: {', '.join(missing_fields)}")

            # Create database connection
            conn = get_connection()
            cur = conn.cursor()

            # Check if SSN exists in Artist table
            cur.execute("""
                SELECT COUNT(*) 
                FROM Artist 
                WHERE socialSecurityNumber = :ssn
            """, {'ssn': data['socialSecurityNumber']})
            artist_count = cur.fetchone()[0]

            # Check if SSN exists in Collector table
            cur.execute("""
                SELECT COUNT(*) 
                FROM Collector 
                WHERE socialSecurityNumber = :ssn
            """, {'ssn': data['socialSecurityNumber']})
            collector_count = cur.fetchone()[0]

            if artist_count > 0 or collector_count > 0:
                return render_template('add_artist.html', success=False, 
                                    error="❌ This SSN already exists in our database. Please enter a unique value.")

            # Insert the new artist
            cur.execute("""
                INSERT INTO Artist (
                    artistId, firstName, lastName, interviewDate, interviewerName,
                    areaCode, telephoneNumber, street, zip, salesLastYear, salesYearToDate,
                    socialSecurityNumber, usualMedium, usualStyle, usualType
                ) VALUES (
                    artistId_sequence.NEXTVAL, :firstName, :lastName, TO_DATE(:interviewDate, 'YYYY-MM-DD'), :interviewerName,
                    :areaCode, :telephoneNumber, :street, :zip, :salesLastYear, :salesYearToDate,
                    :socialSecurityNumber, :usualMedium, :usualStyle, :usualType
                )
            """, data)

            conn.commit()
            return render_template('add_artist.html', success=True)

        except oracledb.DatabaseError as e:
            error_msg = str(e)
            print(f"Debug - Database Error: {error_msg}")
            
            if "ORA-12899" in error_msg:
                if "USUALMEDIUM" in error_msg:
                    error = "❌ Medium field exceeds maximum length of 30 characters."
                elif "USUALSTYLE" in error_msg:
                    error = "❌ Style field exceeds maximum length of 30 characters."
                elif "USUALTYPE" in error_msg:
                    error = "❌ Type field exceeds maximum length of 30 characters."
                elif "SOCIALSECURITYNUMBER" in error_msg:
                    error = "❌ SSN must be exactly 9 digits."
                elif "ZIP" in error_msg:
                    error = "❌ ZIP must be exactly 5 digits."
                else:
                    error = "❌ One of your fields is too long. Please check all inputs."
            elif "ORA-00001" in error_msg:  # Unique constraint violation
                if "ARTIST_SSN_PK" in error_msg:
                    error = "❌ This SSN already exists. Please enter a unique value."
                else:
                    print(f"Detailed constraint violation: {error_msg}")  # Add detailed error logging
                    if "SALE_ARTWORK_UK" in error_msg:
                        error = "❌ This artwork has already been sold. Each artwork can only be sold once."
                    else:
                        error = f"❌ A database constraint was violated: {error_msg}"
            elif "SOCIALSECURITYNUMBER" in error_msg and "ORA-12899" in error_msg:
                error = "❌ SSN must be exactly 9 digits (no dashes)."
            elif "ZIP_FK" in error_msg:
                error = "❌ ZIP code not found. Please use a valid U.S. ZIP code."
            elif "ORA-12899" in error_msg and "ZIP" in error_msg:
                error = "❌ ZIP must be 5 digits."
            else:
                error = "❌ Database Error: " + error_msg
                
            if conn:
                conn.rollback()
            return render_template('add_artist.html', success=False, error=error)

        except Exception as e:
            print(f"Debug - Unexpected Error: {str(e)}")
            if conn:
                conn.rollback()
            return render_template('add_artist.html', success=False, 
                                error="❌ An unexpected error occurred. Please try again.")

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('add_artist.html')


@app.route('/add_artwork', methods=['GET', 'POST'])
@login_required
def add_artwork():
    CURRENT_YEAR = 2025  # Set fixed current year
    conn = None
    cur = None
    
    if request.method == 'POST':
        print("DEBUG: Received POST request to /add_artwork")
        print("DEBUG: Form data:", request.form.to_dict())
        
        try:
            # Validate required gallery fields
            date_listed = request.form.get('dateListed', '').strip()
            asking_price = request.form.get('askingPrice', '').strip()
            status = request.form.get('status', '').strip() or 'for sale'  # Default to 'for sale'
            
            print("DEBUG: Gallery fields validation:")
            print(f"- Date Listed: {date_listed}")
            print(f"- Asking Price: {asking_price}")
            print(f"- Status: {status}")
            
            if not date_listed:
                print("DEBUG: Date Listed is missing")
                return render_template('add_artwork.html', success=False,
                                    error="❌ Date Listed is required.")
            if not asking_price:
                print("DEBUG: Asking Price is missing")
                return render_template('add_artwork.html', success=False,
                                    error="❌ Asking Price is required.")
            
            try:
                asking_price = float(asking_price)
                if asking_price <= 0:
                    print("DEBUG: Invalid asking price (<=0)")
                    return render_template('add_artwork.html', success=False,
                                        error="❌ Asking Price must be greater than 0.")
            except ValueError:
                print("DEBUG: Invalid asking price format")
                return render_template('add_artwork.html', success=False,
                                    error="❌ Please enter a valid number for Asking Price.")

            # Step 1: Read name and lookup artistId
            artist_first = request.form.get('artistFirstName', '').strip()
            artist_last = request.form.get('artistLastName', '').strip()

            print("DEBUG: Artist information:")
            print(f"- First Name: {artist_first}")
            print(f"- Last Name: {artist_last}")

            conn = get_connection()
            cur = conn.cursor()

            # Debug print
            print(f"Searching for artist: First Name = '{artist_first}', Last Name = '{artist_last}'")

            # Try case-insensitive search with TRIM to handle extra spaces
            cur.execute("""
                SELECT artistId, firstName, lastName 
                FROM Artist
                WHERE TRIM(LOWER(firstName)) = TRIM(LOWER(:firstName))
                AND TRIM(LOWER(lastName)) = TRIM(LOWER(:lastName))
            """, {'firstName': artist_first, 'lastName': artist_last})
            
            result = cur.fetchone()
            
            # Debug print
            if result:
                print(f"Found artist: ID = {result[0]}, Name = {result[1]} {result[2]}")
            else:
                print("Artist not found, showing all artists for debugging:")
                cur.execute("SELECT firstName, lastName, artistId FROM Artist")
                all_artists = cur.fetchall()
                for artist in all_artists:
                    print(f"- {artist[0]} {artist[1]} (ID: {artist[2]})")

            if not result:
                return render_template('add_artwork.html', success=False,
                                    error=f"❌ Artist not found. Could not find '{artist_first} {artist_last}' in the database.")

            artist_id = result[0]

            # Handle type with "Other" option
            work_type = request.form.get('usualType', '').strip()
            if work_type == 'other':
                work_type = request.form.get('otherType', '').strip()

            # Handle medium with "Other" option
            work_medium = request.form.get('usualMedium', '').strip()
            if work_medium == 'other':
                work_medium = request.form.get('otherMedium', '').strip()

            # Handle style with "Other" option
            work_style = request.form.get('usualStyle', '').strip()
            if work_style == 'other':
                work_style = request.form.get('otherStyle', '').strip()

            # Print form data for debugging
            print("Form data:", {
                'work_type': work_type,
                'work_medium': work_medium,
                'work_style': work_style,
                'title': request.form.get('title', '').strip(),
                'yearCompleted': request.form.get('yearCompleted', '').strip(),
                'size': request.form.get('size', '').strip(),
                'dateListed': date_listed,
                'askingPrice': asking_price,
                'status': status
            })

            # Validate field lengths
            if len(work_type) > 20:
                return render_template('add_artwork.html', success=False,
                                    error="❌ Type field exceeds 20 characters. Please shorten it.")
            if len(work_medium) > 15:
                return render_template('add_artwork.html', success=False,
                                    error="❌ Medium field exceeds 15 characters. Please shorten it.")
            if len(work_style) > 30:
                return render_template('add_artwork.html', success=False,
                                    error="❌ Style field exceeds 30 characters. Please shorten it.")

            # Step 2: Collect the rest of the data
            year_completed = request.form.get('yearCompleted', '').strip()
            
            # Validate year format and value
            if not year_completed.isdigit():
                return render_template('add_artwork.html', success=False,
                                    error="❌ Year must contain only digits.")
            
            if len(year_completed) != 4:
                return render_template('add_artwork.html', success=False,
                                    error="❌ Year must be exactly 4 digits (e.g., 2024).")
            
            year_completed_int = int(year_completed)
            
            if year_completed_int > CURRENT_YEAR:
                return render_template('add_artwork.html', success=False,
                                    error=f"❌ Year cannot be beyond {CURRENT_YEAR}.")

            data = {
                'artistId': artist_id,
                'workTitle': request.form.get('title', '').strip(),
                'workYearCompleted': year_completed,
                'workType': work_type,
                'workMedium': work_medium,
                'workStyle': work_style,
                'workSize': request.form.get('size', '').strip(),
                'collectorSocialSecurityNumber': request.form.get('ownerSSN', '').strip() or None,
                'dateListed': date_listed,
                'askingPrice': asking_price,
                'status': status
            }

            # Print collected data for debugging
            print("Data to be inserted:", data)

            # Basic required fields
            required_fields = ['workTitle', 'workYearCompleted', 'workType',
                           'workMedium', 'workStyle', 'workSize',
                           'dateListed', 'askingPrice', 'status']
            
            missing_fields = [field for field in required_fields if not data[field]]
            if missing_fields:
                print("Missing fields:", missing_fields)  # Debug print
                return render_template('add_artwork.html', success=False,
                                    error=f"❌ The following required fields are missing: {', '.join(missing_fields)}")

            # Step 3: Insert into Artwork table
            cur.execute("""
                INSERT INTO Artwork (
                    artworkId, artistId, workTitle, workYearCompleted, workType,
                    workMedium, workStyle, workSize, collectorSocialSecurityNumber,
                    dateListed, askingPrice, status
                ) VALUES (
                    artworkId_sequence.NEXTVAL, :artistId, :workTitle, :workYearCompleted, :workType,
                    :workMedium, :workStyle, :workSize, :collectorSocialSecurityNumber,
                    TO_DATE(:dateListed, 'YYYY-MM-DD'), :askingPrice, :status
                )
            """, data)

            conn.commit()
            return render_template('add_artwork.html', success=True)

        except oracledb.DatabaseError as e:
            error_msg = str(e)
            if "ORA-12899" in error_msg:
                if "WORKTITLE" in error_msg:
                    error = "❌ Title is too long. Max 100 characters."
                elif "WORKTYPE" in error_msg:
                    error = "❌ Type too long. Max 20 characters."
                elif "WORKMEDIUM" in error_msg:
                    error = "❌ Medium too long. Max 15 characters."
                elif "WORKSTYLE" in error_msg:
                    error = "❌ Style too long. Max 30 characters."
                elif "WORKSIZE" in error_msg:
                    error = "❌ Size too long. Max 25 characters."
                else:
                    error = "❌ One or more inputs exceed the allowed length. Please shorten your entries."
            elif "ORA-01722" in error_msg:
                error = "❌ Please make sure all numeric fields (Year, Price) are valid numbers."
            elif "ORA-01400" in error_msg:
                error = "❌ A required field is missing. Please fill out all fields marked with a red asterisk."
            elif "ORA-00001" in error_msg and "ARTWORK_ARTISTID_TITLE_UK" in error_msg:
                error = "❌ An artwork with this title already exists for this artist. Please use a different title."
            elif "ORA-02291" in error_msg:
                if "ARTWORK_COLLECTORSOCIALSECURITYNUMBER_FK" in error_msg:
                    error = "❌ The Owner SSN you entered does not exist in our collector database. Please first register this person as a collector using the 'Add Collector' form, or leave the SSN field blank if they are not a collector."
                elif "ARTWORK_ARTISTID_FK" in error_msg:
                    error = "❌ The specified artist does not exist in our database. Please verify the artist name."
                else:
                    error = "❌ A database reference constraint failed. Please check that all entered IDs and references exist in our system."
            else:
                error = "❌ An error occurred while saving the artwork. Please check your input and try again."

            if conn:
                conn.rollback()
            return render_template('add_artwork.html', success=False, error=error)

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Unexpected error: {str(e)}")
            return render_template('add_artwork.html', success=False,
                                error="❌ An unexpected error occurred. Please try again.")

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('add_artwork.html', current_year=CURRENT_YEAR)

@app.route('/add_sale', methods=['GET', 'POST'])
@login_required
def add_sale():
    print("\n=== Starting add_sale route ===")
    print(f"Request method: {request.method}")
    
    if request.method == 'POST':
        print("\n=== Processing POST request for sale ===")
        print("Raw form data received:", request.form.to_dict())
        
        conn = None
        cur = None
        try:
            # Step 1: Validate and collect form data
            print("\n=== Step 1: Collecting form data ===")
            data = {
                'artworkTitle': request.form.get('artworkTitle', '').strip(),
                'artistLastName': request.form.get('artistLastName', '').strip(),
                'artistFirstName': request.form.get('artistFirstName', '').strip(),
                'buyerLastName': request.form.get('buyerLastName', '').strip(),
                'buyerFirstName': request.form.get('buyerFirstName', '').strip(),
                'buyerStreet': request.form.get('buyerStreet', '').strip(),
                'buyerCity': request.form.get('buyerCity', '').strip(),
                'buyerState': request.form.get('buyerState', '').strip(),
                'buyerZip': request.form.get('buyerZip', '').strip(),
                'buyerAreaCode': request.form.get('buyerAreaCode', '').strip(),
                'buyerPhoneNumber': request.form.get('buyerPhoneNumber', '').strip(),
                'salePrice': request.form.get('salePrice', '').strip(),
                'saleTax': request.form.get('saleTax', '').strip(),
                'amountRemittedToOwner': request.form.get('amountRemittedToOwner', '').strip(),
                'salespersonSSN': request.form.get('salespersonSSN', '').strip(),
                'saleDate': request.form.get('saleDate', '').strip()
            }
            
            print("\nRaw numeric values from form:")
            print(f"Sale Price (raw): '{data['salePrice']}'")
            print(f"Sale Tax (raw): '{data['saleTax']}'")
            print(f"Amount Remitted (raw): '{data['amountRemittedToOwner']}'")

            # Store form data in session
            session['sale_form_data'] = data
            print("Stored form data in session")

            # Validate required fields first
            required_fields = [
                'artworkTitle', 'artistLastName', 'artistFirstName',
                'buyerLastName', 'buyerFirstName', 'buyerStreet', 'buyerZip',
                'buyerAreaCode', 'buyerPhoneNumber', 'salePrice', 'saleTax',
                'amountRemittedToOwner', 'salespersonSSN', 'saleDate'
            ]
            
            missing_fields = [field for field in required_fields if not data[field]]
            if missing_fields:
                print(f"Missing required fields: {missing_fields}")
                return render_template('add_sale.html', 
                    error=f"❌ Required fields missing: {', '.join(missing_fields)}",
                    form_data=data)

            conn = get_connection()
            cur = conn.cursor()

            print("\n=== Step 2: Looking up artwork ===")
            print(f"Searching for artwork: '{data['artworkTitle']}' by {data['artistFirstName']} {data['artistLastName']}")
            
            # Lookup artwork ID from title and artist name
            cur.execute("""
                SELECT A.artworkId, A.askingPrice
                FROM Artwork A
                JOIN Artist R ON A.artistId = R.artistId
                WHERE LOWER(A.workTitle) = LOWER(:title)
                  AND LOWER(R.firstName) = LOWER(:firstName)
                  AND LOWER(R.lastName) = LOWER(:lastName)
            """, {
                'title': data['artworkTitle'],
                'firstName': data['artistFirstName'],
                'lastName': data['artistLastName']
            })
            artwork_row = cur.fetchone()

            if not artwork_row:
                print("Artwork not found")
                return render_template('add_sale.html', 
                    error="❌ Artwork not found. Please verify the title and artist name.",
                    form_data=data)

            artwork_id = artwork_row[0]
            asking_price = float(artwork_row[1])
            print(f"Found artwork ID: {artwork_id}, Asking Price: {asking_price}")

            # Check if artwork is already sold
            cur.execute("""
                SELECT S.invoiceNumber, S.saleDate
                FROM Sale S
                WHERE S.artworkId = :artworkId
            """, {'artworkId': artwork_id})
            
            existing_sale = cur.fetchone()
            if existing_sale:
                print(f"Artwork already sold: Invoice #{existing_sale[0]} on {existing_sale[1]}")
                return render_template('add_sale.html', 
                    error=f"❌ This artwork has already been sold (Invoice #{existing_sale[0]} on {existing_sale[1].strftime('%Y-%m-%d')})",
                    form_data=data)

            print("\n=== Step 3: Looking up buyer ===")
            print(f"Searching for buyer: {data['buyerFirstName']} {data['buyerLastName']}")
            
            # Look for existing collector (buyer)
            cur.execute("""
                SELECT SOCIALSECURITYNUMBER, firstName, lastName, street, zip 
                FROM Collector
                WHERE LOWER(firstName) = LOWER(:firstName)
                  AND LOWER(lastName) = LOWER(:lastName)
                  AND LOWER(street) = LOWER(:street)
                  AND zip = :zip
            """, {
                'firstName': data['buyerFirstName'],
                'lastName': data['buyerLastName'],
                'street': data['buyerStreet'],
                'zip': data['buyerZip']
            })
            collector = cur.fetchone()
            
            if not collector:
                print("Buyer not found in collector database")
                return render_template('add_sale.html', 
                    error=f"❌ Buyer '{data['buyerFirstName']} {data['buyerLastName']}' not found in collector database. Please verify the name and address or register them as a collector first.",
                    form_data=data)

            buyer_ssn = collector[0]
            print(f"Found buyer SSN: {buyer_ssn}")

            print("\n=== Step 4: Verifying salesperson ===")
            # Verify salesperson exists
            cur.execute("""
                SELECT COUNT(*) 
                FROM Salesperson 
                WHERE socialSecurityNumber = :ssn
            """, {'ssn': data['salespersonSSN']})
            
            if cur.fetchone()[0] == 0:
                print("Salesperson not found")
                return render_template('add_sale.html', 
                    error="❌ Salesperson not found. Please verify the SSN.",
                    form_data=data)

            print("Salesperson verified")

            print("\n=== Step 5: Validating numeric fields ===")
            try:
                # Convert strings to float and round to 2 decimal places
                print("Converting string values to floats...")
                
                try:
                    sale_price = float(data['salePrice'])
                    print(f"Converted sale price: {sale_price}")
                except ValueError as e:
                    print(f"Error converting sale price: {e}")
                    return render_template('add_sale.html', 
                        error="❌ Invalid sale price format",
                        form_data=data)

                try:
                    sale_tax = float(data['saleTax'])
                    print(f"Converted sale tax: {sale_tax}")
                except ValueError as e:
                    print(f"Error converting sale tax: {e}")
                    return render_template('add_sale.html', 
                        error="❌ Invalid sale tax format",
                        form_data=data)

                try:
                    amount_remitted = float(data['amountRemittedToOwner'])
                    print(f"Converted amount remitted: {amount_remitted}")
                except ValueError as e:
                    print(f"Error converting amount remitted: {e}")
                    return render_template('add_sale.html', 
                        error="❌ Invalid amount remitted format",
                        form_data=data)

                # Format to exactly 2 decimal places
                print("\nFormatting to exact decimal places...")
                sale_price = float('{:.2f}'.format(sale_price))
                sale_tax = float('{:.2f}'.format(sale_tax))
                amount_remitted = float('{:.2f}'.format(amount_remitted))

                print(f"Formatted values:")
                print(f"Sale price: {sale_price} (type: {type(sale_price)})")
                print(f"Sale tax: {sale_tax} (type: {type(sale_tax)})")
                print(f"Amount remitted: {amount_remitted} (type: {type(amount_remitted)})")

                # Additional validations
                if sale_price <= 0:
                    return render_template('add_sale.html', 
                        error="❌ Sale price must be greater than zero",
                        form_data=data)
                
                if sale_tax < 0:
                    return render_template('add_sale.html', 
                        error="❌ Sale tax cannot be negative",
                        form_data=data)
                
                if amount_remitted <= 0:
                    return render_template('add_sale.html', 
                        error="❌ Amount remitted must be greater than zero",
                        form_data=data)
                
                if amount_remitted >= sale_price:
                    return render_template('add_sale.html', 
                        error="❌ Amount remitted to owner cannot be greater than or equal to sale price",
                        form_data=data)

                print("\n=== Step 6: Preparing for database insertion ===")
                print("Converting numeric values to strings with exact precision...")
                
                # Convert to strings with exact precision for database
                sale_price_str = "{:.2f}".format(sale_price)
                sale_tax_str = "{:.2f}".format(sale_tax)
                amount_remitted_str = "{:.2f}".format(amount_remitted)

                print(f"Database-ready values:")
                print(f"Sale price string: '{sale_price_str}'")
                print(f"Sale tax string: '{sale_tax_str}'")
                print(f"Amount remitted string: '{amount_remitted_str}'")

                # Create a variable for the returning invoice number
                invoice_var = cur.var(int)

                print("\n=== Step 7: Executing database insertion ===")
                # Insert into Sale table
                insert_query = """
                    INSERT INTO Sale (
                        INVOICENUMBER, ARTWORKID, AMOUNTREMITTEDTOOWNER,
                        SALEDATE, SALEPRICE, SALETAX, BUYERID, SALESPERSONSSN
                    ) VALUES (
                        SALEID_SEQUENCE.NEXTVAL, :artworkId, :amountRemittedToOwner,
                        TO_DATE(:saleDate, 'YYYY-MM-DD'), :salePrice, :saleTax,
                        :buyerSSN, :salespersonSSN
                    ) RETURNING INVOICENUMBER INTO :invoice_number
                """
                
                print("Executing INSERT with parameters:")
                insert_params = {
                    'artworkId': artwork_id,
                    'amountRemittedToOwner': amount_remitted_str,
                    'saleDate': data['saleDate'],
                    'salePrice': sale_price_str,
                    'saleTax': sale_tax_str,
                    'salespersonSSN': data['salespersonSSN'],
                    'buyerSSN': buyer_ssn,
                    'invoice_number': invoice_var
                }
                print("Parameters:", insert_params)
                
                cur.execute(insert_query, insert_params)
                
                invoice_number = invoice_var.getvalue()[0]
                print(f"Sale recorded successfully with invoice number: {invoice_number}")

                # Update artwork status to 'Sold'
                print("\nUpdating artwork status to 'Sold'")
                cur.execute("""
                    UPDATE Artwork
                    SET status = 'Sold'
                    WHERE artworkId = :artwork_id
                """, {'artwork_id': artwork_id})

                conn.commit()
                print("Transaction committed successfully")
                
                # Clear session data after successful sale
                session.pop('sale_form_data', None)
                
                return render_template('add_sale.html', 
                    success=True,
                    message=f"✅ Sale completed successfully! Invoice number: {invoice_number}")

            except oracledb.DatabaseError as e:
                error_msg = str(e)
                print(f"\n=== Database Error Details ===")
                print(f"Error message: {error_msg}")
                print(f"Error code: {e.code if hasattr(e, 'code') else 'Unknown'}")
                print(f"Error offset: {e.offset if hasattr(e, 'offset') else 'Unknown'}")
                
                if "ORA-01438" in error_msg:
                    print("\nPrecision error details:")
                    print(f"Sale price: {sale_price_str if 'sale_price_str' in locals() else 'Not converted'}")
                    print(f"Sale tax: {sale_tax_str if 'sale_tax_str' in locals() else 'Not converted'}")
                    print(f"Amount remitted: {amount_remitted_str if 'amount_remitted_str' in locals() else 'Not converted'}")
                
                if conn:
                    conn.rollback()
                return render_template('add_sale.html', error=f"❌ Database Error: {error_msg}", form_data=data)

        except Exception as e:
            print(f"\n=== Unexpected Error ===")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            import traceback
            print("Traceback:")
            print(traceback.format_exc())
            if conn:
                conn.rollback()
            return render_template('add_sale.html',
                error=f"❌ An unexpected error occurred: {str(e)}",
                form_data=data)

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
            print("\n=== Request processing completed ===")

    # When loading the form (GET request)
    print("Processing GET request")
    form_data = session.get('sale_form_data', {})
    print("Retrieved form data from session:", form_data)
    return render_template('add_sale.html', form_data=form_data)


@app.route('/add_mailing_list', methods=['GET', 'POST'])
@login_required
def add_mailing():
    if request.method == 'POST':
        preferred_artist_name = (
            request.form.get('preferredArtistFirstName', '').strip() + ' ' +
            request.form.get('preferredArtistLastName', '').strip()
        ).strip()

        data = {
            'signupDate': request.form['signupDate'],
            'firstName': request.form['firstName'].strip(),
            'lastName': request.form['lastName'].strip(),
            'street': request.form['street'].strip(),
            'zip': request.form['zip'].strip(),
            'areaCode': request.form['areaCode'].strip(),
            'telephoneNumber': request.form['telephoneNumber'].replace('-', '').strip(),
            'preferredMedium': request.form.get('preferredMedium', '').strip(),
            'preferredStyle': request.form.get('preferredStyle', '').strip(),
            'preferredType': request.form.get('preferredType', '').strip()
        }

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Check for duplicate entry
            cur.execute("""
                SELECT COUNT(*) FROM PotentialCustomer
                WHERE LOWER(firstName) = LOWER(:firstName)
                  AND LOWER(lastName) = LOWER(:lastName)
                  AND LOWER(street) = LOWER(:street)
                  AND zip = :zip
                  AND telephoneNumber = :telephoneNumber
            """, {
                'firstName': data['firstName'],
                'lastName': data['lastName'],
                'street': data['street'],
                'zip': data['zip'],
                'telephoneNumber': data['telephoneNumber']
            })

            if cur.fetchone()[0] > 0:
                return render_template('add_mailing_list.html', success=False,
                    error="❌ This person is already on the mailing list with the same address and phone number.")

            # Get artistId only if a name was provided
            if preferred_artist_name:
                cur.execute("""
                    SELECT artistId FROM Artist
                    WHERE LOWER(firstName || ' ' || lastName) = LOWER(:name)
                """, {'name': preferred_artist_name})
                artist_row = cur.fetchone()
                preferred_artist_id = artist_row[0] if artist_row else None
            else:
                preferred_artist_id = None

            # Insert
            cur.execute("""
                INSERT INTO PotentialCustomer (
                    potentialCustomerId, firstName, lastName, areaCode, telephoneNumber,
                    street, zip, dateFilledIn, preferredArtistId, preferredMedium, preferredStyle, preferredType
                ) VALUES (
                    potentialCustomerId_sequence.NEXTVAL, :firstName, :lastName, :areaCode, :telephoneNumber,
                    :street, :zip, TO_DATE(:signupDate, 'YYYY-MM-DD'), :preferredArtistId,
                    :preferredMedium, :preferredStyle, :preferredType
                )
            """, {
                **data,
                'preferredArtistId': preferred_artist_id
            })

            conn.commit()
            cur.close()
            conn.close()
            return render_template('add_mailing_list.html', success=True)

        except oracledb.DatabaseError as e:
            error_msg = str(e)

            if "ORA-12899" in error_msg:
                if "ZIP" in error_msg:
                    error = "❌ ZIP code must be 5 digits."
                elif "AREACODE" in error_msg:
                    error = "❌ Area Code must be exactly 3 digits."
                elif "TELEPHONENUMBER" in error_msg:
                    error = "❌ Phone Number must be 7 digits."
                else:
                    error = "❌ One of the fields is too long. Please check your input."
            elif "ORA-01722" in error_msg:
                error = "❌ Please ensure ZIP, Area Code, and Phone Number are numbers only."
            elif "ORA-01400" in error_msg:
                error = "❌ A required field is missing. Please fill in all required fields marked *."
            elif "ORA-01745" in error_msg:
                error = "❌ Internal error: Check all fields for unusual characters or spacing."
            else:
                error = "❌ Database Error: " + error_msg

            return render_template('add_mailing_list.html', success=False, error=error)

    return render_template('add_mailing_list.html', success=False)




@app.route('/add_collector', methods=['GET', 'POST'])
@login_required
def add_collector():
    if request.method == 'POST':
        conn = None
        cur = None
        try:
            print("DEBUG: Starting form processing")  # Debug log
            artist_first = request.form.get('collectionArtistFirstName', '').strip()
            artist_last = request.form.get('collectionArtistLastName', '').strip()
            artist_name = f"{artist_first} {artist_last}".strip()

            # Handle collection type with "Other" option
            collection_type = request.form.get('collectionType', '').strip()
            if collection_type == 'other':
                collection_type = request.form.get('otherTypeInput', '').strip()

            # Handle collection medium with "Other" option
            collection_medium = request.form.get('collectionMedium', '').strip()
            if collection_medium == 'other':
                collection_medium = request.form.get('otherMediumInput', '').strip()

            # Handle collection style with "Other" option
            collection_style = request.form.get('collectionStyle', '').strip()
            if collection_style == 'other':
                collection_style = request.form.get('otherStyleInput', '').strip()

            print(f"DEBUG: Collection details - Type: {collection_type}, Medium: {collection_medium}, Style: {collection_style}")  # Debug log

            # Validate field lengths before database operation
            if len(collection_type) > 30:
                return render_template('add_collector.html', success=False,
                                    error="❌ Collection Type exceeds 30 characters. Please shorten it.")
            if len(collection_medium) > 30:
                return render_template('add_collector.html', success=False,
                                    error="❌ Collection Medium exceeds 30 characters. Please shorten it.")
            if len(collection_style) > 30:
                return render_template('add_collector.html', success=False,
                                    error="❌ Collection Style exceeds 30 characters. Please shorten it.")

            # Validate required fields
            required_fields = {
                'interviewDate': request.form.get('interviewDate', '').strip(),
                'interviewerName': request.form.get('interviewerName', '').strip(),
                'firstName': request.form.get('firstName', '').strip(),
                'lastName': request.form.get('lastName', '').strip(),
                'street': request.form.get('street', '').strip(),
                'zip': request.form.get('zip', '').strip(),
                'areaCode': request.form.get('areaCode', '').strip(),
                'telephoneNumber': request.form.get('telephoneNumber', '').strip(),
                'socialSecurityNumber': request.form.get('socialSecurityNumber', '').strip()
            }

            # Check for missing required fields
            missing_fields = [field for field, value in required_fields.items() if not value]
            if missing_fields:
                return render_template('add_collector.html', success=False,
                                    error=f"❌ Required fields missing: {', '.join(missing_fields)}")

            print("DEBUG: All required fields present")  # Debug log

            data = {
                'socialSecurityNumber': required_fields['socialSecurityNumber'].replace("-", ""),
                'firstName': required_fields['firstName'],
                'lastName': required_fields['lastName'],
                'street': required_fields['street'],
                'zip': required_fields['zip'],
                'interviewDate': required_fields['interviewDate'],
                'interviewerName': required_fields['interviewerName'],
                'areaCode': required_fields['areaCode'],
                'telephoneNumber': required_fields['telephoneNumber'],
                'salesLastYear': request.form.get('salesLastYear', 0),
                'salesYearToDate': request.form.get('salesYearToDate', 0),
                'collectionMedium': collection_medium,
                'collectionStyle': collection_style,
                'collectionType': collection_type
            }

            print("DEBUG: Data prepared for database", data)  # Debug log

            conn = get_connection()
            cur = conn.cursor()

            # ✅ Only try to look up artistId if artist name is provided
            collection_artist_id = None
            if artist_name:
                print(f"DEBUG: Looking up artist: {artist_name}")  # Debug log
                cur.execute("""
                    SELECT artistId FROM Artist
                    WHERE LOWER(firstName || ' ' || lastName) = LOWER(:name)
                """, {'name': artist_name})
                row = cur.fetchone()
                if not row:
                    return render_template('add_collector.html', success=False,
                                           error="❌ Artist not found. Leave artist fields blank if not applicable.")
                collection_artist_id = row[0]

            print("DEBUG: Inserting into database")  # Debug log
            cur.execute("""
                INSERT INTO Collector (
                    socialSecurityNumber, firstName, lastName, street, zip,
                    interviewDate, interviewerName, areaCode, telephoneNumber,
                    salesLastYear, salesYearToDate, collectionArtistId,
                    collectionMedium, collectionStyle, collectionType
                ) VALUES (
                    :socialSecurityNumber, :firstName, :lastName, :street, :zip,
                    TO_DATE(:interviewDate, 'YYYY-MM-DD'), :interviewerName, :areaCode, :telephoneNumber,
                    :salesLastYear, :salesYearToDate, :collectionArtistId,
                    :collectionMedium, :collectionStyle, :collectionType
                )
            """, {**data, 'collectionArtistId': collection_artist_id})

            conn.commit()
            print("DEBUG: Database insert successful")  # Debug log
            return render_template('add_collector.html', success=True)

        except oracledb.DatabaseError as e:
            error_msg = str(e)
            print(f"DEBUG: Database error: {error_msg}")  # Debug log
            if "COLLECTOR_SSN_PK" in error_msg:
                error = "❌ This SSN already exists. Use a unique SSN."
            elif "ZIP_FK" in error_msg:
                error = "❌ ZIP code not found. Use a valid ZIP."
            elif "ORA-12899" in error_msg:
                if "SOCIALSECURITYNUMBER" in error_msg:
                    error = "❌ SSN must be exactly 9 digits."
                elif "ZIP" in error_msg:
                    error = "❌ ZIP must be exactly 5 digits."
                elif "COLLECTIONTYPE" in error_msg:
                    error = "❌ Collection Type exceeds maximum length of 30 characters."
                elif "COLLECTIONMEDIUM" in error_msg:
                    error = "❌ Collection Medium exceeds maximum length of 30 characters."
                elif "COLLECTIONSTYLE" in error_msg:
                    error = "❌ Collection Style exceeds maximum length of 30 characters."
                else:
                    error = "❌ One of your fields is too long. Please check all inputs."
            else:
                error = f"❌ Database Error: {error_msg}"

            if conn:
                conn.rollback()
            return render_template('add_collector.html', success=False, error=error)

        except Exception as e:
            print(f"DEBUG: Unexpected error: {str(e)}")  # Debug log
            if conn:
                conn.rollback()
            return render_template('add_collector.html', success=False,
                                error=f"❌ An unexpected error occurred: {str(e)}")

        finally:
            if 'cur' in locals() and cur:
                cur.close()
            if 'conn' in locals() and conn:
                conn.close()
            print("DEBUG: Database connection closed")  # Debug log

    return render_template('add_collector.html', success=False)

@app.route('/profile')
@login_required
def profile():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user information
        cursor.execute("""
            SELECT username, email, first_name, last_name
            FROM users 
            WHERE user_id = :user_id
        """, user_id=session['user_id'])
        
        user_data = cursor.fetchone()
        if user_data:
            user = {
                'username': user_data[0],
                'email': user_data[1],
                'first_name': user_data[2],
                'last_name': user_data[3]
            }
            return render_template('profile.html', user=user)
        else:
            return redirect(url_for('logout'))
            
    except Exception as e:
        print(f"Profile error: {str(e)}")
        flash('An error occurred while loading your profile', 'error')
        return redirect(url_for('index'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        email = request.form['email']
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if email is already used by another user
        cursor.execute("""
            SELECT 1 FROM users 
            WHERE email = :email AND user_id != :user_id
        """, email=email, user_id=session['user_id'])
        
        if cursor.fetchone():
            flash('Email address is already in use', 'error')
            return redirect(url_for('profile'))
        
        # Update user information
        cursor.execute("""
            UPDATE users 
            SET first_name = :first_name,
                last_name = :last_name,
                email = :email
            WHERE user_id = :user_id
        """, first_name=first_name, last_name=last_name, 
             email=email, user_id=session['user_id'])
        
        conn.commit()
        
        # Update session name
        session['user_name'] = f"{first_name} {last_name}"
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))
        
    except Exception as e:
        print(f"Profile update error: {str(e)}")
        flash('An error occurred while updating your profile', 'error')
        return redirect(url_for('profile'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        current_password = request.form['currentPassword']
        new_password = request.form['newPassword']
        confirm_new_password = request.form['confirmNewPassword']
        
        # Validate new password
        if len(new_password) < 8:
            flash('New password must be at least 8 characters long', 'error')
            return redirect(url_for('profile'))
        if not any(c.isalpha() for c in new_password):
            flash('New password must contain at least one letter', 'error')
            return redirect(url_for('profile'))
        if not any(c.isdigit() for c in new_password):
            flash('New password must contain at least one number', 'error')
            return redirect(url_for('profile'))
        if new_password != confirm_new_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('profile'))
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verify current password
        cursor.execute("""
            SELECT password_hash 
            FROM users 
            WHERE user_id = :user_id
        """, user_id=session['user_id'])
        
        user_data = cursor.fetchone()
        if not user_data or not check_password_hash(user_data[0], current_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('profile'))
        
        # Update password
        new_password_hash = generate_password_hash(new_password)
        cursor.execute("""
            UPDATE users 
            SET password_hash = :password_hash
            WHERE user_id = :user_id
        """, password_hash=new_password_hash, user_id=session['user_id'])
        
        conn.commit()
        flash('Password changed successfully', 'success')
        return redirect(url_for('profile'))
        
    except Exception as e:
        print(f"Password change error: {str(e)}")
        flash('An error occurred while changing your password', 'error')
        return redirect(url_for('profile'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
