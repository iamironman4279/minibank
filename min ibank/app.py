from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

def init_db():
    conn = sqlite3.connect('pycash.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            amount REAL,
            recipient TEXT,
            date TEXT,
            memo TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS balance (
            id INTEGER PRIMARY KEY,
            total REAL
        )
    ''')
    c.execute('SELECT COUNT(*) FROM balance')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO balance (id, total) VALUES (1, 0)')
    conn.commit()
    conn.close()

init_db()

def update_balance(amount, operation):
    conn = sqlite3.connect('pycash.db')
    c = conn.cursor()
    c.execute('SELECT total FROM balance WHERE id = 1')
    current_balance = c.fetchone()[0]
    new_balance = current_balance + amount if operation == 'deposit' else current_balance - amount
    c.execute('UPDATE balance SET total = ? WHERE id = 1', (new_balance,))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_payment', methods=['GET', 'POST'])
def add_payment():
    if request.method == 'POST':
        amount = float(request.form['dollars'])
        payment_to = request.form['paymentTo']
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        memo = request.form.get('memo', '')

        conn = sqlite3.connect('pycash.db')
        c = conn.cursor()
        c.execute('SELECT total FROM balance WHERE id = 1')
        current_balance = c.fetchone()[0]

        if amount > current_balance:
            flash('Insufficient funds!')
            return redirect(url_for('add_payment'))
        
        c.execute('''
            INSERT INTO transactions (type, amount, recipient, date, memo)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Payment', amount, payment_to, date, memo))
        conn.commit()
        conn.close()

        update_balance(amount, 'payment')

        return redirect(url_for('index'))
    return render_template('add_payment.html')

@app.route('/add_deposit', methods=['GET', 'POST'])
def add_deposit():
    if request.method == 'POST':
        amount = float(request.form['dollars'])
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        memo = request.form.get('memo', '')

        conn = sqlite3.connect('pycash.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO transactions (type, amount, recipient, date, memo)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Deposit', amount, '', date, memo))
        conn.commit()
        conn.close()

        update_balance(amount, 'deposit')

        return redirect(url_for('index'))
    return render_template('add_deposit.html')

@app.route('/view_finances', methods=['GET'])
def view_finances():
    conn = sqlite3.connect('pycash.db')
    c = conn.cursor()
    c.execute('SELECT * FROM transactions')
    transactions = c.fetchall()
    c.execute('SELECT total FROM balance WHERE id = 1')
    balance = c.fetchone()[0]
    conn.close()
    return render_template('view_finances.html', transactions=transactions, balance=balance)

@app.route('/generate_pdf')
def generate_pdf():
    conn = sqlite3.connect('pycash.db')
    c = conn.cursor()
    c.execute('SELECT * FROM transactions')
    transactions = c.fetchall()
    c.execute('SELECT total FROM balance WHERE id = 1')
    balance = c.fetchone()[0]
    conn.close()

    pdf_buffer = io.BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(30, height - 30, "Transaction Statement")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(30, height - 60, "Type")
    pdf.drawString(120, height - 60, "Amount")
    pdf.drawString(210, height - 60, "Date")
    pdf.drawString(300, height - 60, "From")

    y = height - 80
    pdf.setFont("Helvetica", 12)
    for transaction in transactions:
        transaction_type, amount, recipient, date, memo = transaction[1], transaction[2], transaction[3], transaction[4], transaction[5]
        pdf.drawString(30, y, transaction_type)
        pdf.drawString(120, y, f"₹{amount:.2f}")
        pdf.drawString(210, y, date)
        pdf.drawString(300, y, From)
        y -= 20

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(30, y - 20, f"Current Balance: ₹{balance:.2f}")

    pdf.save()
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True, download_name='statement.pdf', mimetype='application/pdf')

@app.route('/clear_transactions', methods=['POST'])
def clear_transactions():
    conn = sqlite3.connect('pycash.db')
    c = conn.cursor()
    c.execute('DELETE FROM transactions')
    c.execute('UPDATE balance SET total = 0 WHERE id = 1')
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
