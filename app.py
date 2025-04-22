from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import pickle
import numpy as np

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'flaskuser'
app.config['MYSQL_PASSWORD'] = 'yourpassword'
app.config['MYSQL_DB'] = 'user_db'

mysql = MySQL(app)

with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

@app.route('/')
def home():
    return render_template('hii.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['userid']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        try:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO login (userid, username, email, password) VALUES (%s, %s, %s, %s)",
                        (userid, username, email, password))
            mysql.connection.commit()
            cur.close()

            session['userid'] = userid
            session['username'] = username

            return redirect(url_for('home'))
        except Exception as e:
            return render_template('login.html', prediction_text=f"Login failed: {str(e)}")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    try:
        cur = mysql.connection.cursor()

        cur.execute("SELECT COUNT(*) FROM login")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM prediction")
        total_predictions = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM prediction WHERE result LIKE '%will buy%'")
        buy_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM prediction WHERE result LIKE '%will not buy%'")
        not_buy_count = cur.fetchone()[0]

        cur.close()

        if total_predictions > 0:
            buy_percentage = round((buy_count / total_predictions) * 100, 2)
            not_buy_percentage = round((not_buy_count / total_predictions) * 100, 2)
        else:
            buy_percentage = not_buy_percentage = 0

        return render_template('dashboard.html',
                               total_users=total_users,
                               total_predictions=total_predictions,
                               buy_percentage=buy_percentage,
                               not_buy_percentage=not_buy_percentage)

    except Exception as e:
        return f"Dashboard error: {str(e)}"

@app.route('/history')
def history():
    if 'userid' not in session:
        return redirect(url_for('login'))

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM prediction WHERE userid = %s", [session['userid']])
        predictions = cur.fetchall()
        cur.close()

        return render_template('history.html', predictions=predictions)

    except Exception as e:
        return render_template('hii.html', prediction_text=f"Error fetching history: {str(e)}")

@app.route('/delete_all_history', methods=['POST'])
def delete_all_history():
    if 'userid' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM prediction WHERE userid = %s", [session['userid']])
        mysql.connection.commit()
        cur.close()

        flash("All prediction history deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting history: {str(e)}", "danger")

    return redirect(url_for('history'))

@app.route('/predict', methods=['POST'])
def predict():
    if 'userid' not in session:
        return redirect(url_for('login'))

    try:
        age = int(request.form['age'])
        salary = int(request.form['salary'])
        gender = request.form['gender']
        gender_val = 1 if gender == 'Male' else 0

        
        input_data = np.array([[gender_val, age, salary]])
        prediction = model.predict(input_data)
        result = "The person will buy the product." if prediction == 1 else "The person will not buy the product."

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO prediction (userid, age, salary, gender, result) VALUES (%s, %s, %s, %s, %s)",
                    (session['userid'], age, salary, gender, result))
        mysql.connection.commit()
        cur.close()

        return render_template('hii.html', prediction_text=result)

    except Exception as e:
        return render_template('hii.html', prediction_text="There was an error with the prediction.")

if __name__ == "__main__":
    app.run(debug=True)
