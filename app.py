from flask import Flask, render_template, request, redirect
from db import get_connection
import oracledb
import re
from datetime import datetime


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_artist', methods=['GET', 'POST'])
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
def add_artwork():
    CURRENT_YEAR = 2025  # Set fixed current year
    
    if request.method == 'POST':
        # Step 1: Read name and lookup artistId
        artist_first = request.form.get('artistFirstName', '').strip()
        artist_last = request.form.get('artistLastName', '').strip()

        try:
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
            """, {
                'firstName': artist_first,
                'lastName': artist_last
            })
            
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
            work_type = request.form.get('type', '').strip()
            if work_type == 'other':
                work_type = request.form.get('otherTypeInput', '').strip()

            # Handle medium with "Other" option
            work_medium = request.form.get('medium', '').strip()
            if work_medium == 'other':
                work_medium = request.form.get('otherMediumInput', '').strip()

            # Handle style with "Other" option
            work_style = request.form.get('style', '').strip()
            if work_style == 'other':
                work_style = request.form.get('otherStyleInput', '').strip()

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
                'dateListed': request.form.get('dateListed'),
                'askingPrice': request.form.get('askingPrice')
            }

            # Validate required fields
            if not all([data['workTitle'], data['workYearCompleted'], data['workType'],
                       data['workMedium'], data['workStyle'], data['workSize'],
                       data['dateListed'], data['askingPrice']]):
                return render_template('add_artwork.html', success=False,
                                    error="❌ All required fields must be filled out.")

            # Step 3: Insert into Artwork table
            cur.execute("""
                INSERT INTO Artwork (
                    artworkId, artistId, workTitle, workYearCompleted, workType,
                    workMedium, workStyle, workSize, collectorSocialSecurityNumber,
                    dateListed, askingPrice
                ) VALUES (
                    artworkId_sequence.NEXTVAL, :artistId, :workTitle, :workYearCompleted, :workType,
                    :workMedium, :workStyle, :workSize, :collectorSocialSecurityNumber,
                    TO_DATE(:dateListed, 'YYYY-MM-DD'), :askingPrice
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
                    error = "❌ The provided owner SSN was not found in our database. Please verify the SSN or leave it blank."
                else:
                    error = "❌ One or more reference constraints failed. Please check your input."
            else:
                error = "❌ An error occurred while saving the artwork. Please check your input and try again."

            return render_template('add_artwork.html', success=False, error=error)

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('add_artwork.html', current_year=2025)  # Pass 2025 as current_year to template

@app.route('/add_buyer', methods=['GET', 'POST'])
def add_buyer():
    if request.method == 'POST':
        data = {
            'firstName': request.form['firstName'].strip(),
            'lastName': request.form['lastName'].strip(),
            'street': request.form['street'].strip(),
            'zip': request.form['zip'].strip(),
            'areaCode': request.form['areaCode'].strip(),
            'telephoneNumber': request.form['telephoneNumber'].strip(),
            'purchasesLastYear': request.form.get('purchasesLastYear', 0),
            'purchasesYearToDate': request.form.get('purchasesYearToDate', 0)
        }

        try:
            conn = get_connection()
            cur = conn.cursor()

            # 🔍 Check if a buyer already exists with same name + address
            cur.execute("""
                SELECT COUNT(*) FROM Buyer
                WHERE LOWER(firstName) = LOWER(:firstName)
                  AND LOWER(lastName) = LOWER(:lastName)
                  AND LOWER(street) = LOWER(:street)
                  AND zip = :zip
            """, {
                'firstName': data['firstName'],
                'lastName': data['lastName'],
                'street': data['street'],
                'zip': data['zip']
            })

            count = cur.fetchone()[0]
            if count > 0:
                error = "❌ A buyer with this name and address already exists. Please avoid duplicates."
                return render_template('add_buyer.html', success=False, error=error)

            # ✅ Insert new buyer
            cur.execute("""
                INSERT INTO Buyer (
                    buyerId, firstName, lastName, street, zip, areaCode,
                    telephoneNumber, purchasesLastYear, purchasesYearToDate
                ) VALUES (
                    buyerId_sequence.NEXTVAL, :firstName, :lastName, :street, :zip, :areaCode,
                    :telephoneNumber, :purchasesLastYear, :purchasesYearToDate
                )
            """, data)

            conn.commit()
            cur.close()
            conn.close()

            return render_template('add_buyer.html', success=True)

        except oracledb.IntegrityError as e:
            error_msg = str(e)
            if "ZIP_FK" in error_msg:
                error = "❌ ZIP code not found. Please enter a valid 5-digit ZIP code from our database."
            elif "ORA-12899" in error_msg:
                if "ZIP" in error_msg:
                    error = "❌ ZIP must be exactly 5 digits."
                elif "AREACODE" in error_msg:
                    error = "❌ Area code must be exactly 3 digits."
                elif "TELEPHONENUMBER" in error_msg:
                    error = "❌ Phone number must be exactly 7 digits."
                else:
                    error = "❌ One of your fields is too long. Please shorten your input."
            else:
                error = "❌ Unexpected error: " + error_msg

            return render_template('add_buyer.html', success=False, error=error)

    return render_template('add_buyer.html', success=False)



@app.route('/add_sale', methods=['GET', 'POST'])
def add_sale():
    if request.method == 'POST':
        conn = None
        cur = None
        try:
            # Step 1: Validate and collect form data
            data = {
                'artworkTitle': request.form.get('artworkTitle', '').strip(),
                'artistLastName': request.form.get('artistLastName', '').strip(),
                'artistFirstName': request.form.get('artistFirstName', '').strip(),
                'ownerLastName': request.form.get('ownerLastName', '').strip(),
                'ownerFirstName': request.form.get('ownerFirstName', '').strip(),
                'ownerStreet': request.form.get('ownerStreet', '').strip(),
                'ownerCity': request.form.get('ownerCity', '').strip(),
                'ownerState': request.form.get('ownerState', '').strip(),
                'ownerZip': request.form.get('ownerZip', '').strip(),
                'ownerAreaCode': request.form.get('ownerAreaCode', '').strip(),
                'ownerPhoneNumber': request.form.get('ownerPhoneNumber', '').strip(),
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

            # Validate required fields
            required_fields = [
                'artworkTitle', 'artistLastName', 'artistFirstName',
                'buyerLastName', 'buyerFirstName', 'buyerStreet', 'buyerZip',
                'buyerAreaCode', 'buyerPhoneNumber', 'salePrice', 'saleTax',
                'amountRemittedToOwner', 'salespersonSSN', 'saleDate'
            ]
            
            missing_fields = [field for field in required_fields if not data[field]]
            if missing_fields:
                return render_template('add_sale.html', success=False,
                    error=f"❌ Required fields missing: {', '.join(missing_fields)}")

            # Validate numeric fields
            try:
                sale_price = float(data['salePrice'])
                sale_tax = float(data['saleTax'])
                amount_remitted = float(data['amountRemittedToOwner'])
                
                # Validate price relationships
                if sale_price <= 0:
                    return render_template('add_sale.html', success=False,
                        error="❌ Sale price must be greater than zero")
                
                if sale_tax < 0:
                    return render_template('add_sale.html', success=False,
                        error="❌ Sale tax cannot be negative")
                
                if amount_remitted <= 0:
                    return render_template('add_sale.html', success=False,
                        error="❌ Amount remitted must be greater than zero")
                
                if amount_remitted >= sale_price:
                    return render_template('add_sale.html', success=False,
                        error="❌ Amount remitted to owner cannot be greater than or equal to sale price")
                
            except ValueError:
                return render_template('add_sale.html', success=False,
                    error="❌ Please enter valid numbers for price, tax, and remitted amount")

            # Validate phone numbers and ZIP codes
            if not (data['buyerAreaCode'].isdigit() and len(data['buyerAreaCode']) == 3):
                return render_template('add_sale.html', success=False,
                    error="❌ Buyer area code must be exactly 3 digits")
            
            if not (data['buyerPhoneNumber'].isdigit() and len(data['buyerPhoneNumber']) == 7):
                return render_template('add_sale.html', success=False,
                    error="❌ Buyer phone number must be exactly 7 digits")
            
            if not (data['buyerZip'].isdigit() and len(data['buyerZip']) == 5):
                return render_template('add_sale.html', success=False,
                    error="❌ Buyer ZIP code must be exactly 5 digits")

            # Validate SSN format
            if not (data['salespersonSSN'].isdigit() and len(data['salespersonSSN']) == 9):
                return render_template('add_sale.html', success=False,
                    error="❌ Salesperson SSN must be exactly 9 digits")

            conn = get_connection()
            cur = conn.cursor()

            # Lookup artwork ID from title and artist name
            print(f"DEBUG: Looking for artwork: '{data['artworkTitle']}' by {data['artistFirstName']} {data['artistLastName']}")
            
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
            
            if artwork_row:
                print(f"DEBUG: Found artwork with ID: {artwork_row[0]}, Price: ${artwork_row[1]}")
            else:
                print("DEBUG: No artwork found with these details")
                return render_template('add_sale.html', success=False,
                    error="❌ Artwork not found. Please verify the title and artist name.")

            artwork_id = artwork_row[0]
            asking_price = float(artwork_row[1])

            # After getting the artwork, let's check if it's already in the Sale table
            print(f"DEBUG: Checking if artwork ID {artwork_id} is already in Sale table")
            
            cur.execute("""
                SELECT S.invoiceNumber, S.saleDate
                FROM Sale S
                WHERE S.artworkId = :artworkId
            """, {'artworkId': artwork_id})
            
            existing_sale = cur.fetchone()
            if existing_sale:
                print(f"DEBUG: Found existing sale - Invoice: {existing_sale[0]}, Date: {existing_sale[1]}")
                return render_template('add_sale.html', success=False,
                    error=f"❌ This artwork has already been sold (Invoice #{existing_sale[0]} on {existing_sale[1].strftime('%Y-%m-%d')})")
            else:
                print("DEBUG: No existing sale found - proceeding with sale")

            # Validate sale price against asking price
            if sale_price < (0.9 * asking_price):  # Allow up to 10% discount
                return render_template('add_sale.html', success=False,
                    error=f"❌ Sale price (${sale_price}) cannot be less than 90% of asking price (${asking_price})")

            # Debug print for buyer search
            print(f"Looking for buyer: {data['buyerFirstName']} {data['buyerLastName']} at {data['buyerStreet']}")

            # Lookup buyer ID with case-insensitive search
            cur.execute("""
                SELECT buyerId 
                FROM Buyer
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
            buyer_row = cur.fetchone()
            if not buyer_row:
                # If not found, try a more flexible search and suggest matches
                cur.execute("""
                    SELECT firstName, lastName, street, zip 
                    FROM Buyer
                    WHERE LOWER(firstName) = LOWER(:firstName)
                    AND LOWER(lastName) = LOWER(:lastName)
                """, {
                    'firstName': data['buyerFirstName'],
                    'lastName': data['buyerLastName']
                })
                potential_matches = cur.fetchall()
                
                if potential_matches:
                    match_info = "\n".join([f"- {row[0]} {row[1]}, {row[2]}, {row[3]}" for row in potential_matches])
                    return render_template('add_sale.html', success=False,
                        error=f"❌ Buyer not found with exact address. Found similar buyers:\n{match_info}")
                else:
                    return render_template('add_sale.html', success=False,
                        error="❌ Buyer not found. Please register the buyer first.")

            buyer_id = buyer_row[0]

            # Verify salesperson exists
            cur.execute("""
                SELECT COUNT(*) 
                FROM Salesperson 
                WHERE socialSecurityNumber = :ssn
            """, {'ssn': data['salespersonSSN']})
            
            if cur.fetchone()[0] == 0:
                return render_template('add_sale.html', success=False,
                    error="❌ Salesperson not found. Please verify the SSN.")

            # Insert into Sale table
            try:
                invoice_var = cur.var(int)
                cur.execute("""
                    INSERT INTO Sale (
                        invoiceNumber, artworkId, amountRemittedToOwner,
                        saleDate, salePrice, saleTax,
                        buyerId, salespersonSSN
                    ) VALUES (
                        SALEID_SEQUENCE.NEXTVAL, :artworkId, :amountRemittedToOwner,
                        TO_DATE(:saleDate, 'YYYY-MM-DD'), :salePrice, :saleTax,
                        :buyerId, :salespersonSSN
                    ) RETURNING invoiceNumber INTO :invoice_number
                """, {
                    'artworkId': artwork_id,
                    'amountRemittedToOwner': amount_remitted,
                    'saleDate': data['saleDate'],
                    'salePrice': sale_price,
                    'saleTax': sale_tax,
                    'buyerId': buyer_id,
                    'salespersonSSN': data['salespersonSSN'],
                    'invoice_number': invoice_var
                })
                
                invoice_number = invoice_var.getvalue()[0]
                conn.commit()
                print(f"DEBUG: Sale successful! Invoice number: {invoice_number}")
                return render_template('add_sale.html', 
                                    success=True, 
                                    message=f"✅ Sale completed successfully! Invoice number: {invoice_number}")
            except oracledb.IntegrityError as e:
                error_msg = str(e)
                print(f"DEBUG: IntegrityError during sale: {error_msg}")
                if "ORA-00001" in error_msg and "SALE_ARTWORK_UK" in error_msg:
                    # Try to get the existing sale details
                    cur.execute("""
                        SELECT invoiceNumber, saleDate
                        FROM Sale
                        WHERE artworkId = :artworkId
                    """, {'artworkId': artwork_id})
                    existing_sale = cur.fetchone()
                    if existing_sale:
                        return render_template('add_sale.html', success=False,
                            error=f"❌ This artwork was already sold successfully (Invoice #{existing_sale[0]} on {existing_sale[1].strftime('%Y-%m-%d')})")
                    else:
                        return render_template('add_sale.html', success=False,
                            error="❌ This artwork has already been sold.")
                conn.rollback()
                raise

        except oracledb.DatabaseError as e:
            error_msg = str(e)
            print(f"Database Error: {error_msg}")  # Debug print
            
            if "SALE_SALESPERSONSSN_FK" in error_msg:
                error = "❌ Salesperson SSN not found in the system. Please enter a valid SSN."
            elif "ORA-12899" in error_msg:
                error = "❌ One or more inputs exceed the allowed length. Please shorten your entries."
            elif "ORA-01722" in error_msg:
                error = "❌ Please make sure all numeric fields (Price, Tax, Remitted Amount) are valid numbers."
            elif "ORA-01400" in error_msg:
                error = "❌ A required field is missing. Please fill out all fields marked with a red asterisk."
            elif "ORA-00001" in error_msg:
                print(f"Detailed constraint violation: {error_msg}")  # Add detailed error logging
                if "SALE_ARTWORK_UK" in error_msg:
                    error = "❌ This artwork has already been sold. Each artwork can only be sold once."
                else:
                    error = f"❌ A database constraint was violated: {error_msg}"
            else:
                error = f"❌ Database Error: {error_msg}"

            if conn:
                conn.rollback()
            return render_template('add_sale.html', success=False, error=error)

        except Exception as e:
            print(f"Unexpected Error: {str(e)}")  # Debug print
            if conn:
                conn.rollback()
            return render_template('add_sale.html', success=False,
                error="❌ An unexpected error occurred. Please try again.")

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('add_sale.html')


@app.route('/add_mailing_list', methods=['GET', 'POST'])
@app.route('/add_mailing_list', methods=['GET', 'POST'])
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
                error = "❌ A required field is missing. Please fill in all required fields marked with *."
            elif "ORA-01745" in error_msg:
                error = "❌ Internal error: Check all fields for unusual characters or spacing."
            else:
                error = "❌ Database Error: " + error_msg

            return render_template('add_mailing_list.html', success=False, error=error)

    return render_template('add_mailing_list.html', success=False)




@app.route('/add_collector', methods=['GET', 'POST'])
def add_collector():
    if request.method == 'POST':
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




if __name__ == '__main__':
    app.run(debug=True, port=5001)
