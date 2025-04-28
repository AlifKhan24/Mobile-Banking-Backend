from flask import Flask, request, redirect, render_template, flash, url_for, make_response, jsonify
import pymysql
import bcrypt
import datetime
from datetime import datetime
import random
import string
import threading
from time import sleep
from decimal import Decimal
import logging
import time
import traceback
from datetime import date, timedelta
from flask import jsonify
from flask import jsonify, session
from dateutil.relativedelta import relativedelta
import os
from flask import send_file, request, redirect
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
app.secret_key = 'your_secret_key_here' 

db = pymysql.connect(
    host="localhost",
    user="root",
    password="janina",
    database="mobilebanking",
    cursorclass=pymysql.cursors.DictCursor  
)

def get_user_id_from_cookie():
    return request.cookies.get("user_id")

def set_secure_cookie(response, user_id):
    response.set_cookie("user_id", str(user_id), max_age=3600, httponly=True, secure=True, samesite='Strict')
    return response
def get_db_connection():
    return db

def generate_unique_trx_id(cursor):
    while True:
        trx_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        cursor.execute("SELECT trx_id FROM send_money WHERE trx_id = %s", (trx_id,))
        if not cursor.fetchone():
            return trx_id

@app.route("/home")
def home():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM user_profile WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
    if user:
        return render_template("home.html", user=user)
    else:
        return "User not found", 404

@app.route("/logout")
def logout():
    resp = make_response(redirect("/login"))
    resp.delete_cookie("user_id")
    return resp


#admin_signup
@app.route("/admin_signup", methods=["GET", "POST"])
def admin_signup():
    if request.method == "GET":
        return render_template("admin_signup.html")
    
    try:
        firstName = request.form.get("firstName")
        lastName = request.form.get("lastName")
        dob = request.form.get("dob")
        email = request.form.get("email")
        phone = request.form.get("phone")
        nid = request.form.get("nid")
        password = request.form.get("password")
        # Validation
        if not password:
            return render_template("admin_signup.html", error="Password is required.")

        if len(phone) != 11 or not phone.startswith("01"):
            return render_template("admin_signup.html", error="Enter a valid 11-digit phone number starting with '01'.")

        try:
            dob_date = datetime.strptime(dob, "%Y-%m-%d").date()

        except ValueError:
            return render_template("admin_signup.html", error="Invalid DOB format. Use YYYY-MM-DD.")

        # Check if phone number already exists
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM admin_profile WHERE phone_number = %s", (phone,))
            existing_user = cursor.fetchone()
            if existing_user:
                return render_template("admin_signup.html", phone_error="Phone number already in use")

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()
        # Insert new admin
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO admin_profile 
                (first_name, last_name, dob, email, phone_number, nid, password, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'unauthorized')
            """, (firstName, lastName, dob_date, email, phone, nid, hashed_password))
            db.commit()
        return redirect("/admin_req_submitted")

    except Exception as e:
        traceback.print_exc()
        return render_template("admin_signup.html", error=f"Signup error: {str(e)}")
    
#admin login
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")

    phone = request.form.get("phone")
    password = request.form.get("password")

    print("Phone submitted:", phone)
    print("Password submitted:", password)

    if not phone or not password:
        return render_template("admin_login.html", error="Please fill in all fields.")

    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM admin_profile WHERE phone_number = %s", (phone,))
        admin = cursor.fetchone()

    print("Admin fetched from DB:", admin)

    if not admin:
        return render_template("admin_login.html", error="Admin not found.")
    
    if not bcrypt.checkpw(password.encode("utf-8"), admin["password"].encode("utf-8")):
        return render_template("admin_login.html", error="Invalid password.")

    status = admin.get("status", "unauthorized")
    if status == "unauthorized":
        return render_template("admin_login.html", error="Request pending.")
    elif status == "denied":
        return render_template("admin_login.html", error="Request denied.")

    resp = make_response(redirect("/admin_home"))
    resp = set_secure_cookie(resp, admin["admin_id"])
    return resp

    


#user_signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    try:
        firstName = request.form.get("firstName")
        lastName = request.form.get("lastName")
        dob = request.form.get("dob")
        email = request.form.get("email")
        phone = request.form.get("phone")
        nid = request.form.get("nid")
        password = request.form.get("password")
        # Validating phone number 
        if len(phone) != 11 or not phone.startswith("01"):
            return render_template("signup.html", error="Enter a valid 11-digit phone number starting with '01'.")
        try:
            #dob_date = datetime.datetime.strptime(dob, "%Y-%m-%d").date()
            dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            return render_template("signup.html", error="Invalid DOB format. Use YYYY-MM-DD.")
        # Checking if the phone number already exists
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM user_profile WHERE phone_number = %s", (phone,))
            existing_user = cursor.fetchone()
            if existing_user:
                return render_template("signup.html", phone_error="Phone number already in use")
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        with db.cursor() as cursor:
            cursor.execute("""INSERT INTO user_profile (first_name, last_name, dob, email, phone_number, nid, password, balance, points, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1000, 0, 'active')""", 
                (firstName, lastName, dob_date, email, phone, nid, hashed_password.decode()))
            db.commit()
        return redirect("/login")
    except Exception as e:
        return render_template("signup.html", error=f"Signup error: {str(e)}")


#user_login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    phone = request.form.get("phone")
    password = request.form.get("password")
    if not phone or len(phone) != 11 or not phone.startswith("01"):
        return render_template("login.html", error="Enter a valid 11-digit phone number starting with '01'.")
    
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM user_profile WHERE phone_number = %s", (phone,))
        user = cursor.fetchone()
    
    if user:
        if user["status"] != "active":
            return render_template("account_suspended.html")

        if bcrypt.checkpw(password.encode("utf-8"), user['password'].encode("utf-8")):
            resp = make_response(redirect("/home"))
            resp = set_secure_cookie(resp, user["user_id"])
            return resp

    return render_template("login.html", error="Invalid phone number or password.")

#profile
#profile_page
@app.route('/profile')
def profile():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")
    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT * FROM user_profile WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return "User not found", 404
        profile_data = {
            "username": user["first_name"],
            "name": f"{user['first_name']} {user['last_name']}",
            "phone": user["phone_number"],
            "firstName": user["first_name"],
            "lastName": user["last_name"],
            "dob": user["dob"].strftime("%Y-%m-%d") if user["dob"] else "",
            "email": user["email"],
            "nid": user["nid"],
            "loyaltyPoints": user.get("points", 0),
            "balance": float(user.get("balance", 0.0))
        }
        return render_template('profile.html', profile=profile_data)
    except Exception as e:
        return f"An error occurred: {str(e)}"
    finally:
        cursor.close()

#edit_profile_page
@app.route('/editprofile', methods=['GET'])
def edit_profile():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect('/login')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_profile WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
        if not user:
            flash('User not found', 'error')
            return redirect('/home')
        profile_data = {
            'name': f"{user['first_name']} {user['last_name']}",
            'phone': user['phone_number'],
            'firstName': user['first_name'],
            'lastName': user['last_name'],
            'dob': user['dob'].strftime('%Y-%m-%d') if user['dob'] else '',
            'email': user['email'],
            'nid': user['nid']
        }
        return render_template('editprofile.html', profile=profile_data)
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect('/home')
    
#update profile
@app.route('/updateprofile', methods=['POST'])
def update_profile():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect('/login')
    first_name = request.form['firstName']
    last_name = request.form['lastName']
    dob = request.form['dob']
    email = request.form['email']
    nid = request.form['nid']
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            update_query = """
                UPDATE user_profile
                SET first_name=%s, last_name=%s, dob=%s, email=%s, nid=%s
                WHERE user_id=%s
            """
            cursor.execute(update_query, (first_name, last_name, dob, email, nid, user_id))
        conn.commit()
        flash('Your Profile Updated Successfully.', 'success')
        return redirect(url_for('edit_profile'))
    except Exception as e:
        print("Update failed:", e)
        flash(f'Error updating profile: {str(e)}', 'error')
        return redirect(url_for('edit_profile'))
    


#send money
#send_now
#send_now
@app.route("/send_now", methods=["GET", "POST"])
def send_now():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return render_template("login.html")

    if request.method == "GET":
        # Pre-fill name and phone number from query parameters if provided
        prefill_name = request.args.get("name")
        prefill_phone = request.args.get("phone")
        return render_template("send_now.html", prefill_name=prefill_name, prefill_phone=prefill_phone)

    recipient_phone = request.form.get("recipient_phone")
    recipient_name = request.form.get("recipient_name")
    amount_str = request.form.get("amount")
    save_info = request.form.get("save_info")  # checkbox (value is 'on' if checked)

    try:
        amount = float(amount_str)
        if amount <= 0:
            return render_template("send_now.html", error="Amount must be greater than 0")
    except (ValueError, TypeError):
        return render_template("send_now.html", error="Invalid amount format")

    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM user_profile WHERE phone_number = %s", (recipient_phone,))
        recipient = cursor.fetchone()
        if not recipient:
            return render_template("send_now.html", error="Phone number not registered.")

        cursor.execute("SELECT balance FROM user_profile WHERE user_id = %s", (user_id,))
        sender = cursor.fetchone()
        if not sender:
            return render_template("login.html", error="Log in again")

        if sender['balance'] < amount:
            return render_template("send_now.html", error="Insufficient balance.")

        cursor.execute("SELECT balance, transaction_limit FROM user_profile WHERE user_id = %s", (user_id,))
        sender = cursor.fetchone()
        if sender['transaction_limit'] < amount:
            return render_template("send_now.html", error="Transaction limit reached. Increase your Transaction limit for this transaction.")

        trx_id = generate_unique_trx_id(cursor)

        cursor.execute("""
            INSERT INTO send_money (user_id, phone_no, name, amount, trx_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, recipient_phone, recipient_name, amount, trx_id))

        cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (amount, user_id))
        cursor.execute("UPDATE user_profile SET balance = balance + %s WHERE phone_number = %s", (amount, recipient_phone))

        if save_info == "on":
            try:
                cursor.execute("""
                    INSERT IGNORE INTO saved_details (user_id, name, phone)
                    VALUES (%s, %s, %s)
                """, (user_id, recipient_name, recipient_phone))
            except Exception as e:
                print("Error saving recipient details:", e)

        # Notifications
        cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)",
                       (user_id, f"Sent {amount} to {recipient_name or recipient_phone}"))
        cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)",
                       (recipient['user_id'], f"Received {amount} from User {user_id}"))

        # History
        cursor.execute("""
            INSERT INTO history (user_id, type, trx_id, account, amount)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, "Send Money", trx_id, recipient_phone, -amount))

        db.commit()

    return render_template("home.html", success="Transaction successful!")




#send_money_int page
@app.route('/submit_transaction', methods=['POST'])
def submit_transaction():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401
    try:
        data = request.get_json()
        account_no = data.get('account_no')
        receivers_name = data.get('receivers_name')
        amount = float(data.get('amount'))
        country = data.get('country')
        # Store data in temporary_send_money_international 
        with db.cursor() as cursor:
            trx_id = generate_unique_trx_id(cursor)
            # Delete existing temporary transactions for this user
            cursor.execute("DELETE FROM temporary_send_money_international WHERE user_id = %s", (user_id,))            
            query = """
            INSERT INTO temporary_send_money_international (trx_id, account_no, receivers_name, amount, country, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (trx_id, account_no, receivers_name, amount, country, user_id))
            db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        print(f"Error in submit_transaction: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

#int_money_confirm
@app.route('/int_money_confirm_transaction')
def int_money_confirm_transaction():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")
    try:
        with db.cursor() as cursor:
            # Retrieving the transaction for current user
            query = """SELECT * FROM temporary_send_money_international 
                    WHERE user_id = %s"""
            cursor.execute(query, (user_id,))
            transaction = cursor.fetchone()
        if not transaction:
            return redirect("/send_money_int")
        exchange_rates = {
            'Australia': 77.27,
            'Canada': 85.05,
            'China': 16.67,
            'France': 131.64,
            'Germany': 131.64,
            'Saudi Arabia': 32.39
        }
        amount_in_bdt = float(transaction['amount'])
        country = transaction['country']
        exchange_rate = exchange_rates.get(country, 1)
        amount_in_selected_country = round(amount_in_bdt / exchange_rate, 2)        
        print(f"Debug - Country: {country}, Exchange rate: {exchange_rate}")
        print(f"Debug - Amount in BDT: {amount_in_bdt}, Amount in {country}: {amount_in_selected_country}")
        context = {
            'account_no': transaction['account_no'],
            'receivers_name': transaction['receivers_name'],
            'country': country,
            'amount_in_bdt': amount_in_bdt,
            'amount_in_selected_country': amount_in_selected_country,
            'user_id': user_id,
            'trx_id': transaction['trx_id']
        }
        return render_template('int_money_confirm.html', **context)   
    except Exception as e:
        print(f"Error in int_money_confirm_transaction: {str(e)}")
        return redirect("/send_money_int")

#int_money_confirm page
@app.route('/confirm_send_money', methods=['POST'])
def confirm_send_money():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401
    try:
        print("Form data received:")
        for key, value in request.form.items():
            print(f"{key}: {value}")
        account_no = request.form.get('account_no', '')
        receivers_name = request.form.get('receivers_name', '')
        country = request.form.get('country', '')
        trx_id = request.form.get('trx_id', '')
        try:
            amount_in_bdt = float(request.form.get('amount_in_bdt', '0'))
        except ValueError:
            print("Invalid amount_in_bdt value")
            amount_in_bdt = 0          
        try:
            amount_in_selected_country = float(request.form.get('amount_in_selected_country', '0'))
        except ValueError:
            print("Invalid amount_in_selected_country value")
            amount_in_selected_country = 0       
        print(f"Processed values: account_no={account_no}, receivers_name={receivers_name}, " +
              f"country={country}, amount_in_bdt={amount_in_bdt}, " +
              f"amount_in_selected_country={amount_in_selected_country}, trx_id={trx_id}")
        if not all([account_no, receivers_name, country, trx_id]) or amount_in_bdt <= 0 or amount_in_selected_country <= 0:
            missing_fields = []
            if not account_no: missing_fields.append("account_no")
            if not receivers_name: missing_fields.append("receivers_name")
            if not country: missing_fields.append("country")
            if not trx_id: missing_fields.append("trx_id")
            if amount_in_bdt <= 0: missing_fields.append("amount_in_bdt")
            if amount_in_selected_country <= 0: missing_fields.append("amount_in_selected_country")           
            error_msg = f"Missing or invalid fields: {', '.join(missing_fields)}"
            print(error_msg)
            return jsonify({'status': 'error', 'message': error_msg})
        with db.cursor() as cursor:
            cursor.execute("SELECT balance FROM user_profile WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()           
            if not user:
                print(f"User with ID {user_id} not found")
                return jsonify({'status': 'error', 'message': 'User not found'})          
            cursor.execute("SELECT balance, transaction_limit FROM user_profile WHERE user_id = %s", (user_id,))
            sender = cursor.fetchone()

            if sender['transaction_limit'] < amount_in_bdt:
                return render_template("send_now.html", error="Transaction limit reached. Increase your Transaction limit for this transaction.")   
            if user['balance'] < amount_in_bdt:
                print(f"Insufficient balance. User has {user['balance']}, needs {amount_in_bdt}")
                return jsonify({'status': 'error', 'message': 'Insufficient balance for this transaction'})     
 
            # temp_int_send_money
            cursor.execute("SELECT * FROM temporary_send_money_international WHERE trx_id = %s AND user_id = %s", 
                          (trx_id, user_id))
            temp_transaction = cursor.fetchone()            
            if not temp_transaction:
                print(f"Transaction ID {trx_id} not found for user {user_id}")
                return jsonify({'status': 'error', 'message': 'Invalid transaction. Please try again.'})           
            print(f"Confirming transaction: {trx_id} for user {user_id}")
            try:
                query = """
                INSERT INTO send_money_international (trx_id, account_no, receivers_name, amount_in_bdt, amount_in_selected_country, country, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (trx_id, account_no, receivers_name, amount_in_bdt, amount_in_selected_country, country, user_id))
                print("Transaction inserted into send_money_international table")
            except Exception as insert_error:
                print(f"Error inserting into send_money_international: {str(insert_error)}")
                raise insert_error
            try:
                cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (amount_in_bdt, user_id))
                print(f"Updated user balance. Deducted {amount_in_bdt} BDT")
            except Exception as balance_error:
                print(f"Error updating user balance: {str(balance_error)}")
                raise balance_error          
            #notification
            try:
                cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", 
                           (user_id, f"Sent {amount_in_bdt} BDT internationally to {receivers_name} in {country}"))
                print("Notification added")
                cursor.execute("""
                    INSERT INTO history (user_id, type, trx_id, account, amount)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, "International Money Transfer", trx_id, account_no, -amount_in_bdt))

            except Exception as notif_error:
                print(f"Error adding notification: {str(notif_error)}")
                raise notif_error           
            # Delete temp
            try:
                cursor.execute("DELETE FROM temporary_send_money_international WHERE trx_id = %s", (trx_id,))
                print(f"Deleted temporary transaction {trx_id}")
            except Exception as delete_error:
                print(f"Error deleting temporary transaction: {str(delete_error)}")
                raise delete_error
            db.commit()
            print("Transaction committed successfully")
        return jsonify({'status': 'success', 'message': 'Money sent successfully!'})  
    except Exception as e:
        db.rollback()
        print(f"Error in confirm_send_money: {str(e)}")
        return jsonify({'status': 'error', 'message': f'An error occurred during transaction: {str(e)}'})

#Add money
#add money bank
@app.route("/bank", methods=["GET", "POST"])
def bank():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return render_template("login.html")   
    if request.method == "GET":
        return render_template("bank.html")  
    account_no = request.form.get("accountNo")
    amount = request.form.get("amount")
    if not account_no or not amount:
        return render_template("bank.html", error="Please fill in all fields.")
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        return render_template("bank.html", error="Invalid amount entered.")
    try:
        with db.cursor() as cursor:
            trx_id = generate_unique_trx_id(cursor)
            cursor.execute(""" 
                INSERT INTO add_money_bank (user_id, acc_no, amount, trx_id)
                VALUES (%s, %s, %s, %s)
            """, (user_id, account_no, amount, trx_id))
            cursor.execute("""
                UPDATE user_profile SET balance = balance + %s WHERE user_id = %s
            """, (amount, user_id))
            #notification
            cursor.execute("""
                INSERT INTO notifications (user_id, alerts)
                VALUES (%s, %s)
            """, (user_id, f"Add money from Bank account {account_no} for Taka {amount:.2f} successful, Trx ID: {trx_id}"))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Add Money from Bank", trx_id, account_no, amount))

            db.commit()
        return render_template("bank.html", success=True)  
    except Exception as e:
        db.rollback()
        return render_template("bank.html", error="Something went wrong. Please try again.")

#add money card
@app.route("/card", methods=["GET", "POST"])
def card():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return render_template("login.html")  
    if request.method == "GET":
        return render_template("card.html")    
    account_no = request.form.get("cardNo")
    amount = request.form.get("amount")
    if not account_no or not amount:
        return render_template("card.html", error="Please fill in all fields.") 
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        return render_template("card.html", error="Invalid amount entered.")
    try:
        with db.cursor() as cursor:
            trx_id = generate_unique_trx_id(cursor)
            cursor.execute(""" 
                INSERT INTO add_money_card (user_id, card_no, amount, trx_id)
                VALUES (%s, %s, %s, %s)
            """, (user_id, account_no, amount, trx_id))
            cursor.execute("""
                UPDATE user_profile SET balance = balance + %s WHERE user_id = %s
            """, (amount, user_id))
            #notification
            cursor.execute("""
                INSERT INTO notifications (user_id, alerts)
                VALUES (%s, %s)
            """, (user_id, f"Add money from card account {account_no} for Taka {amount:.2f} successful, Trx ID: {trx_id}"))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Add Money from Card", trx_id, account_no, amount))

            db.commit()
        return render_template("card.html", success=True) 
    except Exception as e:
        db.rollback()
        return render_template("card.html", error="Something went wrong. Please try again.")


#gift card
@app.route("/gift_card", methods=["GET", "POST"])
def gift_card():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")
    if request.method == "GET":
        return render_template("gift_card.html")
    card_code = request.form.get("giftcode", "").strip().upper()
    try:
        with db.cursor() as cursor:
            #Checking if card exists and is active
            cursor.execute(
                "SELECT amount FROM gift_cards WHERE card_no = %s AND status = 'active'",
                (card_code,)
            )
            gift_card = cursor.fetchone()
            if not gift_card:
                return render_template("gift_card.html", error="Invalid redeem code")
            amount = gift_card["amount"]
            cursor.execute(
                "UPDATE user_profile SET balance = balance + %s WHERE user_id = %s",
                (amount, user_id)
            )
            #update card status
            cursor.execute(
                "UPDATE gift_cards SET status = 'used' WHERE card_no = %s",
                (card_code,)
            )
            #notification
            cursor.execute(
                "INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)",
                (user_id, f"Gift card of {amount} Taka Redeemed!")
            )
            db.commit()
            return render_template("gift_card.html", success="Code Redeemed!!!")
    except Exception as e:
        db.rollback()
        return render_template("gift_card.html", error="An error occurred during redemption.")


#Investment
#investments page
@app.route("/invest")
def invest_page():
    with db.cursor() as cursor:
        cursor.execute("SELECT investment_id, name, roi FROM investment_ads")
        investments = cursor.fetchall()
    return render_template("investments.html", investments=investments)
@app.route("/api/get-investment-options")
def get_investment_options():
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT name, roi FROM investment_ads")
            investments = cursor.fetchall()
        return jsonify(investments)
    except Exception as e:
        print("Error fetching investment options:", e)
        return jsonify([]), 500

#investments
@app.route("/api/submit-investment", methods=["POST"])
def submit_investment():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401
    try:
        data = request.get_json()
        investment_name = data.get("option")  # This is the name sent from frontend
        amount = float(data.get("amount", 0))
        period = int(data.get("months", 1))
        if not investment_name or amount <= 0 or not (1 <= period <= 12):
            return jsonify({"success": False, "message": "Invalid input"}), 400
        with db.cursor() as cursor:
            cursor.execute("SELECT investment_id, roi FROM investment_ads WHERE name = %s", (investment_name,))
            investment = cursor.fetchone()
            if not investment:
                return jsonify({"success": False, "message": "Investment option not found"}), 404
            investment_id = investment["investment_id"]
            roi = float(investment["roi"])
            #return amount
            return_amount = round(amount + (amount * (roi / 100) * period), 2)
            trx_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            start_date = datetime.date.today()
            end_date = start_date + datetime.timedelta(days=period * 30)
            cursor.execute("""
                INSERT INTO investment_user (
                    trx_id, user_id, investment_id, amount, period, start_date, end_date, return_amount
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                trx_id, user_id, investment_id, amount, period, start_date, end_date, return_amount
            ))
            db.commit()
            time.sleep(0.5)
        return jsonify({"success": True, "redirect": "/investment_confirmation"})
    except Exception as e:
        print("Error during investment submission:", e)
        return jsonify({"success": False, "message": "Server error"}), 500

#load investment data from investments.html to investment_confirmation.html
@app.route("/api/get-latest-investment")
def get_latest_investment():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401
    try:
        user_id = int(user_id)
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT iu.trx_id, ia.name, iu.return_amount, iu.period
                FROM investment_user iu
                JOIN investment_ads ia ON iu.investment_id = ia.investment_id
                WHERE iu.user_id = %s AND iu.status = 'inactive'
                ORDER BY iu.id DESC
                LIMIT 1
            """, (user_id,))


            investment = cursor.fetchone()
            print("Investment query result:", investment)
            if not investment:
                return jsonify({"success": False, "message": "No pending investment found"}), 404
            investment['return_amount'] = float(investment['return_amount'])
            return jsonify({"success": True, **investment})
    except Exception as e:
        print("Error loading investment:", e)
        return jsonify({"success": False, "message": "Server error"}), 500

#investment confirmation
@app.route("/api/confirm-investment", methods=["POST"])
def confirm_investment():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    try:
        user_id = int(user_id)  
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT iu.trx_id, ia.name, iu.amount, iu.return_amount, iu.period, iu.end_date
                FROM investment_user iu
                JOIN investment_ads ia ON iu.investment_id = ia.investment_id
                WHERE iu.user_id = %s AND iu.status = 'inactive'
                ORDER BY iu.id DESC
                LIMIT 1
            """, (user_id,))


            investment = cursor.fetchone()
            if not investment:
                return jsonify({"success": False, "message": "No inactive investment"}), 404
            amount = investment['amount']
            return_amount = investment['return_amount']
            trx_id = investment['trx_id']
            end_date = investment['end_date']
            name = investment['name']
            period = investment['period']
            cursor.execute("SELECT balance FROM user_profile WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if not user or user['balance'] < amount:
                return jsonify({"success": False, "message": "Insufficient balance"})
            cursor.execute("""
                UPDATE user_profile SET balance = balance - %s WHERE user_id = %s
            """, (amount, user_id))
            cursor.execute("""
                UPDATE investment_user SET status = 'active' WHERE trx_id = %s
            """, (trx_id,))
            #Notification
            cursor.execute("""
                INSERT INTO notifications (user_id, alerts)
                VALUES (%s, %s)
            """, (user_id, f"Successfully invested {amount} Taka on {name} for {period} months."))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Investment", trx_id, name, -amount))

            db.commit()
            #invest period tracker
            def release_return():
                now = datetime.datetime.now().date()
                wait_seconds = (end_date - now).days * 86400
                sleep(max(0, wait_seconds))
                try:
                    with db.cursor() as c:
                        c.execute("UPDATE user_profile SET balance = balance + %s WHERE user_id = %s",
                                  (return_amount, user_id))
                        db.commit()
                except Exception as e:
                    print("Error adding return amount later:", e)
            threading.Thread(target=release_return).start()
            return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        print("Error in investment confirmation:", e)
        return jsonify({"success": False, "message": "Server error"}), 500


#Payment

# Utility
#gas bill
@app.route("/gas_bill", methods=["GET", "POST"])
def gas_bill():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")

    if request.method == "GET":
        return render_template("gas_bill.html")

    name = request.form.get("userName")
    meter_no = request.form.get("meterNo")
    amount = float(request.form.get("amount"))
    month = request.form.get("month")

    installment_option = request.form.get("installmentMonths")
    is_installment = request.form.get("installmentOption") == "on"
    is_multi_source = request.form.get("multipleSourceOption") == "on"

    mobile_percentage = int(request.form.get("mobileSlider", 0)) if is_multi_source else 100
    mobile_share = round((mobile_percentage / 100) * amount, 2)


    with db.cursor() as cursor:
        cursor.execute("SELECT balance, transaction_limit FROM user_profile WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return redirect("/login")

        balance = float(user['balance'])
        trx_limit = int(user['transaction_limit'])

        # INSTALLMENT 
        if is_installment and installment_option:
            months = int(installment_option)
            part1 = round(amount / months, 2)

            if balance < part1:
                return render_template("gas_bill.html", popup="insufficient")
            if part1 > trx_limit:
                return render_template("gas_bill.html", popup="limit")

            cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (part1, user_id))

            due_1_date = (datetime.now() + timedelta(days=30)).date()
            due_2_date = (datetime.now() + timedelta(days=60)).date() if months == 3 else None

            cursor.execute("""
                INSERT INTO pay_gas 
                (user_id, name, meter_no, amount, month, installment, due_1, due_2, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (
                user_id, name, meter_no, amount, month, months, due_1_date, due_2_date
            ))

            cursor.execute("UPDATE user_profile SET points = points + %s WHERE user_id = %s", (int(amount // 100), user_id))

            alert = f"Bill payment for Gas ID {meter_no} of {amount} Taka Successful!"
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))

            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Gas Bill Payment in Installment", "N/A", meter_no, -amount))

            db.commit()
            return render_template("gas_bill.html", popup="success")

        # MULTI-SOURCE 
        elif is_multi_source:
            if balance < mobile_share:
                return render_template("gas_bill.html", popup="insufficient")
            if mobile_share > trx_limit:
                return render_template("gas_bill.html", popup="limit")

            cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (mobile_share, user_id))

            cursor.execute("""
                INSERT INTO pay_gas (user_id, name, meter_no, amount, month, multi_source)
                VALUES (%s, %s, %s, %s, %s, 'yes')
            """, (user_id, name, meter_no, amount, month))

            cursor.execute("UPDATE user_profile SET points = points + %s WHERE user_id = %s", (int(amount // 100), user_id))

            alert = f"Bill payment for Gas ID {meter_no} of {amount} Taka Paid from multiple sources!"
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))

            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Multi Source Gas Bill Payment", "N/A", meter_no, -amount))

            db.commit()
            return render_template("gas_bill.html", popup="success")

        # STANDARD PAYMENT
        else:
            if balance < amount:
                return render_template("gas_bill.html", popup="insufficient")
            if amount > trx_limit:
                return render_template("gas_bill.html", popup="limit")

            cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (amount, user_id))

            cursor.execute("""
                INSERT INTO pay_gas (user_id, name, meter_no, amount, month)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, name, meter_no, amount, month))

            cursor.execute("UPDATE user_profile SET points = points + %s WHERE user_id = %s", (int(amount // 100), user_id))

            alert = f"Bill payment for Gas ID {meter_no} of {amount} Taka Successful!"
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))

            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Gas Bill Payment", "N/A", meter_no, -amount))

            # Cashback Logic
            cursor.execute("SELECT tier FROM user_profile WHERE user_id = %s", (user_id,))
            user_tier = cursor.fetchone()
            if user_tier:
                tier = user_tier['tier'].lower()  # Make it lowercase to match rewards table
                cursor.execute("SELECT cashback_rate FROM rewards WHERE tier = %s", (tier,))
                reward = cursor.fetchone()
                if reward:
                    cashback_amount = (float(reward['cashback_rate']) / 100) * amount
                    cashback_amount = round(cashback_amount, 2)  # Round to 2 decimal places

                    cursor.execute("UPDATE user_profile SET balance = balance + %s WHERE user_id = %s", (cashback_amount, user_id))

                    #cashback history
                    cursor.execute("""
                        INSERT INTO history (user_id, type, trx_id, account, amount)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, "Cashback", "N/A", "Gas Bill", cashback_amount))

                    #cashback notification
                    cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)",
                                (user_id, f"Received {cashback_amount} cashback for Gas Bill Payment"))


            db.commit()
            return render_template("gas_bill.html", popup="success")


#wifi bill
@app.route("/wifi_bill", methods=["GET", "POST"])
def wifi_bill():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")

    if request.method == "GET":
        return render_template("wifi_bill.html")

    name = request.form.get("userName")
    wifi_id = request.form.get("meterNo")
    amount = float(request.form.get("amount"))
    month = request.form.get("month")

    installment_option = request.form.get("installmentMonths")
    is_installment = request.form.get("installmentOption") == "on"
    is_multi_source = request.form.get("multipleSourceOption") == "on"

    mobile_percentage = int(request.form.get("mobileSlider", 0)) if is_multi_source else 100
    mobile_share = round((mobile_percentage / 100) * amount, 2)

    with db.cursor() as cursor:
        cursor.execute("SELECT balance, transaction_limit FROM user_profile WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return redirect("/login")

        balance = float(user['balance'])
        trx_limit = int(user['transaction_limit'])

        # INSTALLMENT 
        if is_installment and installment_option:
            months = int(installment_option)
            part1 = round(amount / months, 2)

            if balance < part1:
                return render_template("wifi_bill.html", popup="insufficient")
            if part1 > trx_limit:
                return render_template("wifi_bill.html", popup="limit")

            cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (part1, user_id))

            due_1_date = (datetime.now() + timedelta(days=30)).date()
            due_2_date = (datetime.now() + timedelta(days=60)).date() if months == 3 else None

            cursor.execute("""
                INSERT INTO pay_wifi 
                (user_id, name, wifi_id, amount, month, installment, due_1, due_2, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (user_id, name, wifi_id, amount, month, months, due_1_date, due_2_date))

            cursor.execute("UPDATE user_profile SET points = points + %s WHERE user_id = %s", (int(amount // 100), user_id))
            alert = f"Bill payment for WiFi ID {wifi_id} of {amount} Taka Successful!"
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "WiFi Bill Payment in Installment", "N/A", wifi_id, -amount))

            db.commit()
            return render_template("wifi_bill.html", popup="success")

        # MULTI-SOURCE 
        elif is_multi_source:
            if balance < mobile_share:
                return render_template("wifi_bill.html", popup="insufficient")
            if mobile_share > trx_limit:
                return render_template("wifi_bill.html", popup="limit")

            cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (mobile_share, user_id))
            cursor.execute("""
                INSERT INTO pay_wifi (user_id, name, wifi_id, amount, month, multi_source)
                VALUES (%s, %s, %s, %s, %s, 'yes')
            """, (user_id, name, wifi_id, amount, month))
            cursor.execute("UPDATE user_profile SET points = points + %s WHERE user_id = %s", (int(amount // 100), user_id))
            alert = f"Bill payment for WiFi ID {wifi_id} of {amount} Taka Paid from multiple sources!"
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Multi Source WiFi Bill Payment", "N/A", wifi_id, -amount))

            db.commit()
            return render_template("wifi_bill.html", popup="success")

        # STANDARD PAYMENT
        else:
            if balance < amount:
                return render_template("wifi_bill.html", popup="insufficient")
            if amount > trx_limit:
                return render_template("wifi_bill.html", popup="limit")

            cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (amount, user_id))
            cursor.execute("""
                INSERT INTO pay_wifi (user_id, name, wifi_id, amount, month)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, name, wifi_id, amount, month))
            cursor.execute("UPDATE user_profile SET points = points + %s WHERE user_id = %s", (int(amount // 100), user_id))
            alert = f"Bill payment for WiFi ID {wifi_id} of {amount} Taka Successful!"
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "WiFi Bill Payment", "N/A", wifi_id, -amount))
            # Cashback Logic
            cursor.execute("SELECT tier FROM user_profile WHERE user_id = %s", (user_id,))
            user_tier = cursor.fetchone()
            if user_tier:
                tier = user_tier['tier'].lower()  # Make it lowercase to match rewards table
                cursor.execute("SELECT cashback_rate FROM rewards WHERE tier = %s", (tier,))
                reward = cursor.fetchone()
                if reward:
                    cashback_amount = (float(reward['cashback_rate']) / 100) * amount
                    cashback_amount = round(cashback_amount, 2)  # Round to 2 decimal places

                    cursor.execute("UPDATE user_profile SET balance = balance + %s WHERE user_id = %s", (cashback_amount, user_id))

                    #cashback history
                    cursor.execute("""
                        INSERT INTO history (user_id, type, trx_id, account, amount)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, "Cashback", "N/A", "WiFi Bill", cashback_amount))

                    #cashback notification
                    cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)",
                                (user_id, f"Received {cashback_amount} cashback for Wifi Bill Payment"))

            db.commit()
            return render_template("wifi_bill.html", popup="success")



#electricity bill
from flask import request, render_template, redirect
from datetime import datetime, timedelta

@app.route("/electricity_bill", methods=["GET", "POST"])
def electricity_bill():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")

    if request.method == "GET":
        return render_template("electricity_bill.html")

    name = request.form.get("userName")
    meter_no = request.form.get("meterNo")
    amount = float(request.form.get("amount"))
    month = request.form.get("month")

    installment_option = request.form.get("installmentMonths")
    is_installment = request.form.get("installmentOption") == "on"
    is_multi_source = request.form.get("multipleSourceOption") == "on"

    mobile_percentage = int(request.form.get("mobileSlider", 0)) if is_multi_source else 100
    mobile_share = round((mobile_percentage / 100) * amount, 2)

    with db.cursor() as cursor:
        cursor.execute("SELECT balance, transaction_limit FROM user_profile WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return redirect("/login")

        balance = float(user['balance'])
        trx_limit = int(user['transaction_limit'])

        # INSTALLMENT MODE
        if is_installment and installment_option:
            months = int(installment_option)
            part1 = round(amount / months, 2)

            if balance < part1:
                return render_template("electricity_bill.html", popup="insufficient")
            if part1 > trx_limit:
                return render_template("electricity_bill.html", popup="limit")

            cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (part1, user_id))

            due_1_date = (datetime.now() + timedelta(days=30)).date()
            due_2_date = (datetime.now() + timedelta(days=60)).date() if months == 3 else None

            cursor.execute("""
                INSERT INTO pay_electricity 
                (user_id, name, meter_no, amount, month, installment, due_1, due_2, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (
                user_id, name, meter_no, amount, month, months, due_1_date, due_2_date
            ))
            #points
            cursor.execute("UPDATE user_profile SET points = points + %s WHERE user_id = %s", (int(amount // 100), user_id))
            #Notification
            alert = f"Bill payment for Meter ID {meter_no} of {amount} Taka Successful!"
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Electricity Bill Payment in Installment", "N/A", meter_no, -amount))

            db.commit()
            return render_template("electricity_bill.html", popup="success")


        # MULTI-SOURCE MODE
        elif is_multi_source:
            if balance < mobile_share:
                return render_template("electricity_bill.html", popup="insufficient")
            if mobile_share > trx_limit:
                return render_template("electricity_bill.html", popup="limit")

            # Deduct the mobile portion
            if mobile_share > 0:
                cursor.execute(
                    "UPDATE user_profile SET balance = balance - %s WHERE user_id = %s",
                    (mobile_share, user_id)
                )

            cursor.execute("""
                INSERT INTO pay_electricity (user_id, name, meter_no, amount, month, multi_source)
                VALUES (%s, %s, %s, %s, %s, 'yes')
            """, (user_id, name, meter_no, amount, month))
            #points
            cursor.execute("UPDATE user_profile SET points = points + %s WHERE user_id = %s", (int(amount // 100), user_id))
            #Notification
            alert = f"Bill payment for Meter ID {meter_no} of {amount} Taka Paid from multiple sources!"
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Multi Source Electricity Bill Payment", "N/A", meter_no, -amount))

            db.commit()
            return render_template("electricity_bill.html", popup="success")


        # STANDARD PAYMENT
        else:
            if balance < amount:
                return render_template("electricity_bill.html", popup="insufficient")
            if amount > trx_limit:
                return render_template("electricity_bill.html", popup="limit")

            cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (amount, user_id))
            cursor.execute("""
                INSERT INTO pay_electricity (user_id, name, meter_no, amount, month)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, name, meter_no, amount, month)) 
            #points
            cursor.execute("UPDATE user_profile SET points = points + %s WHERE user_id = %s", (int(amount // 100), user_id))
            #Notification
            alert = f"Bill payment for Electricity Meter {meter_no} of {amount} Taka Successful!"
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Electricity Bill Payment", "N/A", meter_no, -amount))
            # Cashback Logic
            cursor.execute("SELECT tier FROM user_profile WHERE user_id = %s", (user_id,))
            user_tier = cursor.fetchone()
            if user_tier:
                tier = user_tier['tier'].lower()  # Make it lowercase to match rewards table
                cursor.execute("SELECT cashback_rate FROM rewards WHERE tier = %s", (tier,))
                reward = cursor.fetchone()
                if reward:
                    cashback_amount = (float(reward['cashback_rate']) / 100) * amount
                    cashback_amount = round(cashback_amount, 2)  # Round to 2 decimal places

                    cursor.execute("UPDATE user_profile SET balance = balance + %s WHERE user_id = %s", (cashback_amount, user_id))

                    #cashback history
                    cursor.execute("""
                        INSERT INTO history (user_id, type, trx_id, account, amount)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, "Cashback", "N/A", "Electricity Bill", cashback_amount))

                    #cashback notification
                    cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)",
                                (user_id, f"Received {cashback_amount} cashback for Electricity Bill Payment"))

            db.commit()
            return render_template("electricity_bill.html", popup="success")
        




#Pending Installment 
from dateutil.relativedelta import relativedelta
@app.route("/pending_installments")
def pending_installments():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")

    all_installments = []

    def fetch_due(cursor, table, id_field, label):
        cursor.execute(f"""
            SELECT amount, installment, due_1, due_2 FROM {table}
            WHERE user_id = %s AND status = 'pending'
        """, (user_id,))
        rows = cursor.fetchall()

        for row in rows:
            amt_per = round(row['amount'] / row['installment'], 2)

            if row['due_1']:
                due1 = row['due_1']
                issue1 = due1 - relativedelta(months=1)
                all_installments.append({
                    "service": label,
                    "amount": amt_per,
                    "issue_date": issue1.strftime("%d/%m/%y"),
                    "due_date": due1.strftime("%d/%m/%y")
                })

            if row['due_2']:
                due2 = row['due_2']
                issue2 = due2 - relativedelta(months=2)
                all_installments.append({
                    "service": label,
                    "amount": amt_per,
                    "issue_date": issue2.strftime("%d/%m/%y"),
                    "due_date": due2.strftime("%d/%m/%y")
                })

    with db.cursor() as cursor:
        fetch_due(cursor, "pay_electricity", "meter_no", "Electricity Bill Payment")
        fetch_due(cursor, "pay_gas", "meter_no", "Gas Bill Payment")
        fetch_due(cursor, "pay_wifi", "wifi_id", "WiFi Bill Payment")

    return render_template("pending_installments.html", installments=all_installments)



# Request Loan
@app.route("/api/request-loan", methods=["POST"])
def request_loan():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    try:
        data = request.get_json()
        amount = float(data.get("amount", 0))
        duration = int(data.get("duration", 0))

        if amount <= 0 or duration not in range(1, 7):
            return jsonify({"success": False, "message": "Invalid input"}), 400

        interest_rates = {
            1: 5,
            2: 5.5,
            3: 6,
            4: 6.5,
            5: 7,
            6: 7.5
        }

        interest_rate = interest_rates[duration]
        return_amount = round(amount + (amount * (interest_rate / 100)), 2)

        trx_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO loans (
                    trx_id, user_id, loan_amount, interest_rate, duration, return_amount, status,
                    issue_date, end_date
                ) VALUES (%s, %s, %s, %s, %s, %s, 'pending', NULL, NULL)
            """, (
                trx_id, user_id, amount, interest_rate, duration, return_amount
            ))
            db.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.rollback()
        print("Loan request error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500


# Set Transaction Limit
@app.route("/set_limit", methods=["GET", "POST"])
def set_limit():
    user_id = get_user_id_from_cookie()

    if request.method == "GET":
        if not user_id:
            return redirect("/login") 

        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT transaction_limit FROM user_profile WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                transaction_limit = result["transaction_limit"] if result else "Unavailable"
        except Exception as e:
            print("Error fetching transaction limit:", e)
            transaction_limit = "Unavailable"

        return render_template("transaction_limit.html", transaction_limit=transaction_limit)
    try:
        data = request.get_json()
        amount = int(data.get("amount", 0))

        if amount <= 0:
            return jsonify({"success": False, "message": "Invalid amount"}), 400

        with db.cursor() as cursor:
            cursor.execute("UPDATE user_profile SET transaction_limit = %s WHERE user_id = %s", (amount, user_id))
            alert = f"Your Transaction Limit has been updated to {amount} Taka per transaction."
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))
            db.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.rollback()
        print("Transaction limit update error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500


# Approvals
@app.route("/approvals", methods=["GET", "POST"])
def approvals():
    if request.method == "GET":
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT first_name, last_name, email, nid, dob, phone_number
                    FROM admin_profile
                    WHERE status = 'unauthorized'
                    ORDER BY admin_id ASC
                    LIMIT 10
                """)
                pending_admins = cursor.fetchall()
        except Exception as e:
            print("Error fetching approvals:", e)
            pending_admins = []
        return render_template("admin_approvals.html", pending_admins=pending_admins)

    elif request.method == "POST":
        try:
            phones = request.form.getlist("phones")
            actions = request.form.getlist("actions")

            updates = list(zip(phones, actions))
            with db.cursor() as cursor:
                for phone, action in updates:
                    if action == "Approve":
                        cursor.execute("UPDATE admin_profile SET status = 'authorized' WHERE phone_number = %s", (phone,))
                    elif action == "Deny":
                        cursor.execute("UPDATE admin_profile SET status = 'denied' WHERE phone_number = %s", (phone,))
            db.commit()
            flash("Approvals updated successfully!", "success")
        except Exception as e:
            print("Error processing approvals:", e)
            flash("Something went wrong. Try again.", "error")

        return redirect("/approvals")

###

def add_months(start_date, months):
    year = start_date.year + ((start_date.month - 1 + months) // 12)
    month = (start_date.month - 1 + months) % 12 + 1
    day = min(start_date.day, [31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    return date(year, month, day)


# Approve Loans
import traceback
@app.route("/approve_loans", methods=["GET", "POST"])
def approve_loans():
    if request.method == "GET":
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT trx_id, user_id, loan_amount, duration, return_amount
                    FROM loans
                    WHERE status = 'pending'
                    ORDER BY trx_id ASC
                    LIMIT 10
                """)
                pending_loans = cursor.fetchall()
        except Exception as e:
            print("Error fetching loans:", e)
            pending_loans = []
        return render_template("approve_loans.html", pending_loans=pending_loans)

    elif request.method == "POST":
        trx_ids = request.form.getlist("trx_ids")
        statuses = request.form.getlist("statuses")

        try:
            with db.cursor() as cursor:
                for trx_id, status in zip(trx_ids, statuses):
                    if status not in ("approved", "denied"):
                        continue

                    cursor.execute("SELECT user_id, loan_amount, duration FROM loans WHERE trx_id = %s", (trx_id,))
                    loan_info = cursor.fetchone()
                    if not loan_info:
                        continue

                    user_id = loan_info["user_id"]
                    loan_amount = loan_info["loan_amount"]
                    duration = loan_info["duration"]

                    alert_msg = f"Your loan of {loan_amount} has been {status}."
                    cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert_msg))

                    if status == "approved":
                        issue_date = date.today()
                        end_date = add_months(issue_date, duration)
                        cursor.execute("""
                            UPDATE loans 
                            SET status = %s, issue_date = %s, end_date = %s 
                            WHERE trx_id = %s
                        """, (status, issue_date, end_date, trx_id))
                        cursor.execute("UPDATE user_profile SET balance = balance + %s WHERE user_id = %s", (loan_amount, user_id))
                    else:
                        cursor.execute("UPDATE loans SET status = %s WHERE trx_id = %s", (status, trx_id))

            db.commit()
            flash("Loan approvals updated successfully!", "success")
        except Exception as e:
            db.rollback()
            print("Error updating loans:", e)
            flash("An error occurred while processing approvals.", "error")

        return redirect("/approve_loans")


# See Active Loans
@app.route("/active_loans")
def active_loans():
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT trx_id, user_id, loan_amount, interest_rate, duration,
                       issue_date, end_date, return_amount
                FROM loans
                WHERE status = 'approved'
            """)
            active_loans = cursor.fetchall()
    except Exception as e:
        print("Error loading active loans:", e)
        active_loans = []

    return render_template("active_loans.html", active_loans=active_loans)


# Pay Loan
@app.route("/pay_loan/<trx_id>", methods=["POST"])
def pay_loan(trx_id):
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT user_id, return_amount FROM loans WHERE trx_id = %s AND status = 'approved'", (trx_id,))
            loan = cursor.fetchone()
            if not loan:
                return jsonify({"status": "error", "message": "Loan not found or already paid."})

            user_id = loan["user_id"]
            amount_due = loan["return_amount"]
            cursor.execute("SELECT balance FROM user_profile WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if not user or user["balance"] < amount_due:
                return jsonify({"status": "error", "message": "Insufficient Balance"})
            cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (amount_due, user_id))
            cursor.execute("DELETE FROM loans WHERE trx_id = %s", (trx_id,))

            #Notification
            alert = f"Your loan of {amount_due} has been fully paid."
            cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (user_id, alert))
            cursor.execute("""
                INSERT INTO history (user_id, type, trx_id, account, amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "Loan Payment", "N/A", "N/A", amount_due))

        db.commit()
        return jsonify({"status": "success"})
    
    except Exception as e:
        print("Loan payment error:", e)
        db.rollback()
        return jsonify({"status": "error", "message": "An error occurred"})



# History
@app.route("/history")
def history():
    user_id = request.cookies.get("user_id")

    if not user_id:
        return "User not logged in or session expired", 401

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT type, trx_id, account, time, amount
                FROM history
                WHERE user_id = %s
                ORDER BY time DESC
            """, (user_id,))
            history_records = cursor.fetchall()
    except Exception as e:
        history_records = []

    return render_template("history.html", history_records=history_records)


# Undo Transaction
@app.route("/cancel_transaction/<trx_id>", methods=["POST"])
def cancel_transaction(trx_id):
    user_id = request.cookies.get("user_id")
    print("Cancel request for trx_id:", trx_id, "| user_id:", user_id)

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT amount FROM history
                WHERE LOWER(trx_id) = LOWER(%s) AND user_id = %s
            """, (trx_id, user_id))
            result = cursor.fetchone()

            if not result:
                print("Transaction not found")
                return jsonify({"status": "error", "message": "Transaction not found"})

            amount = result["amount"]
            cursor.execute("""
                SELECT * FROM admin_reports
                WHERE user_id = %s AND trx_id = %s AND report_type = 'Request Cancellation'
            """, (user_id, trx_id))
            if cursor.fetchone():
                return jsonify({"status": "exists", "message": "Already requested"})

            cursor.execute("""
                INSERT INTO admin_reports (user_id, report_type, trx_id, amount)
                VALUES (%s, 'Request Cancellation', %s, %s)
            """, (user_id, trx_id, amount))

        db.commit()
        print("Cancellation logged.")
        return jsonify({"status": "success"})

    except Exception as e:
        print("Error:", e)
        db.rollback()
        return jsonify({"status": "error", "message": "Internal server error"})


# Admin Reports
@app.route("/admin_reports", methods=["GET", "POST"])
def admin_reports():
    if request.method == "POST":
        trx_ids = request.form.getlist("trx_ids[]")

        for i in range(len(trx_ids)):
            trx_id = trx_ids[i]
            action = request.form.get(f"actions_{i}")
            remark = request.form.get(f"remarks_{i}")

            print(f" Processing trx_id: {trx_id} | Action: {action} | Remark: {remark}")

            if not action or action.strip() == "":
                continue

            try:
                with db.cursor() as cursor:
                    cursor.execute("""
                        UPDATE admin_reports
                        SET actions = %s, remarks = %s
                        WHERE trx_id = %s AND report_type = 'Request Cancellation'
                    """, (action, remark, trx_id))

                    if action.lower() != "approve":
                        continue
                    cursor.execute("SELECT user_id, type FROM history WHERE trx_id = %s", (trx_id,))
                    hist = cursor.fetchone()
                    if not hist:
                        continue

                    user_id = hist["user_id"]
                    trx_type = hist["type"].lower()

                    if trx_type == "send money":
                        cursor.execute("SELECT amount, phone_no FROM send_money WHERE trx_id = %s", (trx_id,))
                        row = cursor.fetchone()
                        if row:
                            amount = row["amount"]
                            phone_no = row["phone_no"]


                            cursor.execute("UPDATE user_profile SET balance = balance + %s WHERE user_id = %s", (amount, user_id))

                            cursor.execute("SELECT user_id FROM user_profile WHERE phone_number = %s", (phone_no,))
                            receiver = cursor.fetchone()
                            if receiver:
                                receiver_id = receiver["user_id"]
                                cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (amount, receiver_id))

                            cursor.execute("DELETE FROM send_money WHERE trx_id = %s", (trx_id,))

                    elif trx_type == "international money transfer":
                        cursor.execute("SELECT amount_in_bdt FROM send_money_international WHERE trx_id = %s", (trx_id,))
                        row = cursor.fetchone()
                        if row:
                            amount = row["amount_in_bdt"]
                            cursor.execute("UPDATE user_profile SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
                            cursor.execute("DELETE FROM send_money_international WHERE trx_id = %s", (trx_id,))

                    cursor.execute("DELETE FROM history WHERE trx_id = %s", (trx_id,))

                db.commit()
                print("Successfully processed and committed.")

            except Exception as e:
                print(f"Error processing trx_id {trx_id}:", e)
                db.rollback()

        return redirect("/admin_reports")

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT user_id, trx_id, report_type, amount
                FROM admin_reports
                WHERE report_type = 'Request Cancellation' AND (actions IS NULL OR actions = 'pending')
                ORDER BY report_id ASC
                LIMIT 10
            """)
            cancel_requests = cursor.fetchall()
    except Exception as e:
        print("Error loading cancel requests:", e)
        cancel_requests = []

    return render_template("admin_reports.html", cancel_requests=cancel_requests)


# Messages
@app.route("/user_messages", methods=["GET", "POST"])
def user_messages():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return "Unauthorized access", 401

    try:
        with db.cursor() as cursor:
            if request.method == "POST":
                message = request.form.get("message")
                if message and message.strip():
                    cursor.execute(
                        "INSERT INTO messages (sender_id, message, role) VALUES (%s, %s, %s)",
                        (user_id, message.strip(), "user")
                    )
                    db.commit()
                    return redirect("/user_messages")


            cursor.execute("""
                SELECT message, role, timestamp
                FROM messages
                WHERE 
                    (sender_id = %s AND role = 'user') OR 
                    (recipient_id = %s AND role = 'admin')
                ORDER BY timestamp ASC
            """, (user_id, user_id))

            messages = cursor.fetchall()

    except Exception as e:
        print(f"Message error: {e}")
        messages = []

    return render_template("user_messages.html", messages=messages)


# Admin Inbox
@app.route("/admin_inbox")
def admin_inbox():
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT m1.sender_id AS user_id,
                       u.phone_number,
                       m1.message,
                       m1.timestamp,
                       EXISTS (
                           SELECT 1 FROM messages m2 
                           WHERE m2.sender_id = m1.sender_id 
                           AND m2.role = 'user' 
                           AND m2.is_read = FALSE
                       ) AS has_unread
                FROM messages m1
                JOIN user_profile u ON m1.sender_id = u.user_id
                WHERE m1.role = 'user'
                AND m1.timestamp = (
                    SELECT MAX(m2.timestamp)
                    FROM messages m2
                    WHERE m2.sender_id = m1.sender_id
                    AND m2.role = 'user'
                )
                ORDER BY m1.timestamp DESC;
            """)
            conversations = cursor.fetchall()
    except Exception as e:
        print("Inbox fetch error:", e)
        conversations = []

    return render_template("admin_inbox.html", conversations=conversations)


# Admin Messages
@app.route("/admin_messages/<int:user_id>", methods=["GET", "POST"])
def admin_messages(user_id):
    admin_id = get_user_id_from_cookie()
    if not admin_id:
        return redirect("/admin_login")

    try:
        with db.cursor() as cursor:
            if request.method == "POST":
                msg = request.form.get("message")
                if msg:

                    cursor.execute("""
                        INSERT INTO messages (sender_id, recipient_id, message, role)
                        VALUES (NULL, %s, %s, 'admin')
                    """, (user_id, msg.strip()))

                    db.commit()
                    return redirect(f"/admin_messages/{user_id}")

            cursor.execute("""
                UPDATE messages 
                SET is_read = TRUE 
                WHERE sender_id = %s AND role = 'user' AND is_read = FALSE
            """, (user_id,))
            db.commit()

            cursor.execute("""
                SELECT message, role, timestamp
                FROM messages
                WHERE (sender_id = %s AND role = 'user') 
                   OR (recipient_id = %s AND role = 'admin')
                ORDER BY timestamp ASC
            """, (user_id, user_id))
            messages = cursor.fetchall()

        return render_template("admin_messages.html", messages=messages, user_id=user_id)
    except Exception as e:
        print("Chat load error:", e)
        return "Internal Server Error", 500


# User Suspend
@app.route('/user_suspend', methods=['GET', 'POST'])
def user_suspend():
    users = []
    selected_user = None
    search_query = ''

    if request.method == 'POST':
        print("POST request received")
        form_data = request.form
        print("Form data:", form_data)

        search_query = form_data.get('search_query') or form_data.get('selected_phone')
        print("Search Query:", search_query)

        if search_query:
            with db.cursor() as cursor:
                query = """
                    SELECT * FROM user_profile
                    WHERE phone_number = %s
                    OR first_name LIKE %s
                    OR last_name LIKE %s
                    OR nid = %s
                """
                cursor.execute(query, (search_query, f"%{search_query}%", f"%{search_query}%", search_query))
                users = cursor.fetchall()

                if users:
                    selected_user = users[0]
                    print("User found:", selected_user)

                    suspend_key = f"status_{selected_user['phone_number']}"
                    if suspend_key in form_data:
                        new_status = form_data[suspend_key]
                        if new_status:
                            update_query = "UPDATE user_profile SET status = %s WHERE phone_number = %s"
                            cursor.execute(update_query, (new_status, selected_user['phone_number']))
                            db.commit()
                            print(f"User {selected_user['phone_number']} status updated to {new_status}")

                            cursor.execute("SELECT * FROM user_profile WHERE phone_number = %s", (selected_user['phone_number'],))
                            updated_user = cursor.fetchone()
                            if updated_user:
                                selected_user = updated_user

    return render_template('user_suspend.html', users=users, selected_user=selected_user, search_query=search_query)



#Notifications
#Notifications_page`
@app.route('/notifications')
def notifications():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect('/login')
    with db.cursor() as cursor:
        cursor.execute("SELECT alerts, timestamp FROM notifications WHERE user_id = %s ORDER BY timestamp DESC", (user_id,))
        notifications = cursor.fetchall()
    return render_template('notifications.html', notifications=notifications)

# Clear Notifications
@app.route('/clear_notifications', methods=['POST'])
def clear_notifications():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect('/login')
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
    db.commit()
    return redirect('/notifications')




@app.route('/download_statements')
def download_statements():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect('/login')
    connection = db
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    #user info
    cursor.execute("SELECT first_name, last_name, email, phone_number FROM user_profile WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()
    if not user:
        connection.close()
        return "User not found"

    # Prepare PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - inch
    logo_path = "templates/logo.png"  
    try:
        pdf.drawImage(logo_path, 40, y - 50, width=100, height=80)
    except:
        pass

    y -= 70
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(200, y, "Transaction Statement")
    y -= 30
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Name: {user['first_name']} {user['last_name']}")
    y -= 15
    pdf.drawString(40, y, f"Email: {user['email']}")
    y -= 15
    pdf.drawString(40, y, f"Phone: {user['phone_number']}")
    y -= 15
    pdf.drawString(40, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 30

    #draw transactions
    def draw_section(title, transactions, headers):
        nonlocal y
        if y < 100:
            pdf.showPage()
            y = height - 50
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, title)
        y -= 20
        pdf.setFont("Helvetica-Bold", 10)
        for i, header in enumerate(headers):
            pdf.drawString(40 + i*100, y, header)
        y -= 15
        pdf.setFont("Helvetica", 10)
        for trx in transactions:
            for i, key in enumerate(headers):
                value = str(trx.get(key.lower(), ''))
                pdf.drawString(40 + i*100, y, value)
            y -= 15
            if y < 100:
                pdf.showPage()
                y = height - 50

    #Retrive data
    queries = [
        ("Added Money (Bank)", "SELECT trx_id, amount FROM add_money_bank WHERE user_id=%s", ['Trx_id', 'Amount']),
        ("Added Money (Card)", "SELECT trx_id, amount FROM add_money_card WHERE user_id=%s", ['Trx_id', 'Amount']),
        ("Sent Money", "SELECT trx_id, amount FROM send_money WHERE user_id=%s", ['Trx_id', 'Amount']),
        ("Sent International", "SELECT trx_id, amount_in_bdt FROM send_money_international WHERE user_id=%s", ['Trx_id', 'Amount_in_bdt']),
        ("Loans", "SELECT trx_id, loan_amount FROM loans WHERE user_id=%s", ['Trx_id', 'Loan_amount']),
        ("Investments", "SELECT trx_id, amount FROM investment_user WHERE user_id=%s", ['Trx_id', 'Amount']),
        ("Electricity Bills", "SELECT meter_no, amount FROM pay_electricity WHERE user_id=%s", ['Meter_no', 'Amount']),
        ("Gas Bills", "SELECT meter_no, amount FROM pay_gas WHERE user_id=%s", ['Meter_no', 'Amount']),
        ("Wi-Fi Bills", "SELECT wifi_id, amount FROM pay_wifi WHERE user_id=%s", ['Wifi_id', 'Amount']),
    ]
    for section_title, query, headers in queries:
        cursor.execute(query, (user_id,))
        records = cursor.fetchall()
        if records:
            draw_section(section_title, records, headers)
            y -= 10
    connection.close()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="statement.pdf", mimetype='application/pdf')

#Schedule Transactions
@app.route("/schedule_transactions", methods=["GET", "POST"])
def schedule_transactions():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")

    if request.method == "GET":
        return render_template("schedule_transactions.html")

    phone = request.form.get("account")
    amount = request.form.get("amount")
    scheduled_time_str = request.form.get("datetime")

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Invalid amount")

        scheduled_time = datetime.strptime(scheduled_time_str, "%Y-%m-%dT%H:%M")

        with db.cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_profile WHERE phone_number = %s", (phone,))
            receiver = cursor.fetchone()

            if not receiver:
                return render_template("schedule_transactions.html", error="Recipient not found.")

            receiver_id = receiver["user_id"]
            cursor.execute("""
                INSERT INTO schedule_transactions (sender_id, receiver_id, amount, scheduled_time)
                VALUES (%s, %s, %s, %s)
            """, (user_id, receiver_id, amount, scheduled_time))
            db.commit()

        return render_template("schedule_transactions.html", success="Transaction scheduled successfully!")
    except Exception as e:
        return render_template("schedule_transactions.html", error="Failed to schedule transaction.")
    
def process_scheduled_transactions():
    while True:
        now = datetime.now()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM schedule_transactions
                WHERE scheduled_time <= %s AND (status IS NULL OR status = 'pending')
            """, (now,))
            transactions = cursor.fetchall()
            for txn in transactions:
                sender_id = txn["sender_id"]
                receiver_id = txn["receiver_id"]
                amount = txn["amount"]
                schedule_id = txn["schedule_id"]

                cursor.execute("SELECT balance FROM user_profile WHERE user_id = %s", (sender_id,))
                sender = cursor.fetchone()
                cursor.execute("SELECT phone_number FROM user_profile WHERE user_id = %s", (receiver_id,))
                receiver_phone = cursor.fetchone()
                receiver_phone = receiver_phone["phone_number"]
                if not sender or sender["balance"] < amount:
                    cursor.execute("UPDATE schedule_transactions SET status = 'cancelled' WHERE schedule_id = %s", (schedule_id,))
                    alert = f"Schedule transfer to {receiver_phone} of {amount} Taka has been cancelled due to insufficient balance."
                    cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (sender_id, alert))
                    continue  

                #Complete transfer
                cursor.execute("UPDATE user_profile SET balance = balance - %s WHERE user_id = %s", (amount, sender_id))
                cursor.execute("UPDATE user_profile SET balance = balance + %s WHERE user_id = %s", (amount, receiver_id))
                alert = f"Schedule transfer to {receiver_phone} of {amount} Taka Successful!"
                cursor.execute("INSERT INTO notifications (user_id, alerts) VALUES (%s, %s)", (sender_id, alert))             
                cursor.execute("""
                    INSERT INTO history (user_id, type, trx_id, account, amount)
                    VALUES (%s, 'Scheduled Send Money', 'N/A', %s, %s)
                """, (sender_id, receiver_phone, -amount))
                #update status
                cursor.execute("UPDATE schedule_transactions SET status = 'completed' WHERE schedule_id = %s", (schedule_id,))
            db.commit()
        sleep(5)

@app.route("/api/pending-scheduled-transactions")
def get_scheduled_transactions():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify([])

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT sp.scheduled_time, sp.amount, up.phone_number AS receiver_phone
                FROM schedule_transactions sp
                JOIN user_profile up ON sp.receiver_id = up.user_id
                WHERE sp.sender_id = %s AND (sp.status IS NULL OR sp.status = 'pending')
                ORDER BY sp.scheduled_time ASC
            """, (user_id,))
            results = cursor.fetchall()
            for row in results:
                if isinstance(row["scheduled_time"], datetime):
                    row["scheduled_time"] = row["scheduled_time"].isoformat()

        return jsonify(results)
    except Exception as e:
        return jsonify([])

#favourite accounts
@app.route("/favourite_accounts", methods=["GET", "POST"])
def favourite_accounts():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return redirect("/login")
    search_query = request.args.get("search", "").strip()
    saved_contacts = []
    try:
        cursor = db.cursor() 
        if search_query:
            cursor.execute("""
                SELECT * FROM saved_details
                WHERE user_id = %s AND (name LIKE %s OR phone LIKE %s)
            """, (user_id, f"%{search_query}%", f"%{search_query}%"))
        else:
            cursor.execute("SELECT * FROM saved_details WHERE user_id = %s", (user_id,))       
        saved_contacts = cursor.fetchall()
    except Exception as e:
        print("Error fetching saved contacts:", e)
    finally:
        cursor.close()
    return render_template("favourite_accounts.html", saved_contacts=saved_contacts)

@app.route("/delete_contact", methods=["POST"])
def delete_contact():
    phone = request.form["phone"]
    user_id = request.cookies.get("user_id")    
    if not user_id:
        return redirect("/login")  
    try:
        with db.cursor() as cursor:
            # Delete contact
            cursor.execute("DELETE FROM saved_details WHERE phone = %s AND user_id = %s", (phone, user_id))
            db.commit()
            return redirect("/favourite_accounts")
    except Exception as e:
        return redirect("/favourite_accounts")



#loyalty points
@app.route('/api/loyalty_points')
def get_loyalty_points():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify({'error': 'User not logged in'}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT points, tier FROM user_profile WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'points': user['points'], 'tier': user['tier']})
    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({'error': 'Server error'}), 500


@app.route('/loyalty_points', methods=['POST'])
def update_loyalty_points():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        new_points = data.get('points')
        if new_points is None:
            return jsonify({"error": "Points not provided"}), 400
        tiers = [
            {"name": "Bronze", "min": 0, "max": 99},
            {"name": "Silver", "min": 100, "max": 299},
            {"name": "Gold", "min": 300, "max": 699},
            {"name": "Platinum", "min": 700, "max": 1199},
            {"name": "Diamond", "min": 1200, "max": float('inf')},
        ]
        new_tier = "Bronze"
        for tier in tiers:
            if new_points >= tier["min"] and new_points <= tier["max"]:
                new_tier = tier["name"]
        cursor.execute("UPDATE user_profile SET points = %s, tier = %s WHERE user_id = %s", (new_points, new_tier, user_id))
        conn.commit()
        return jsonify({"success": True, "new_points": new_points, "new_tier": new_tier})
    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": "Server error"}), 500








#routes
@app.route("/")
def homepage():
    return render_template("landing.html")

@app.route("/scheduled_transactions")
def scheduled_transactions():
    return render_template("scheduled_transactions.html")

@app.route("/admin_home")
def admin_home():
    return render_template("admin_home.html")

@app.route("/add_money")
def add_money():
    return render_template("add_money.html")

@app.route("/investments")
def investments():
    return render_template("investments.html")

@app.route("/send_money")
def send_money():
    return render_template("send_money.html")

@app.route("/investment_confirmation.html")
def investment_confirmation():
    return render_template("investment_confirmation.html")

@app.route("/utility")
def utility():
    return render_template("utility.html")

@app.route("/payment")
def payment():
    return render_template("payment.html")

@app.route("/donations")
def donations():
    return render_template("donations.html")

@app.route("/loan")
def loan():
    return render_template("loan.html")

@app.route("/request_money")
def request_money():
    return render_template("request_money.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/send_money_int")
def send_money_int():
    return render_template("send_money_int.html")

@app.route("/int_money_confirm")
def int_money_confirm():
    return render_template("int_money_confirm.html")

@app.route("/investmentconfirmation")
def investmentconfirmation():
    return render_template("investmentconfirmation.html")


@app.route("/admin_req_submitted")
def admin_req_submitted():
    return render_template("admin_req_submitted.html")

@app.route('/loyalty_points', methods=['GET'])
def loyalty_points_page():
    return render_template('loyalty_points.html')


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=process_scheduled_transactions, daemon=True).start()
    app.run(port=8000, debug=True)



