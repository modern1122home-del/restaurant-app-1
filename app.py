from flask import Flask, render_template, request, redirect, send_file, session
import os
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
import psycopg2.extras

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

app = Flask(__name__)
app.secret_key = "mf-secret"

# ================= DB =================
DATABASE_URL = os.getenv("DATABASE_URL")

def connect():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    db = connect()
    cur = db.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price NUMERIC(10,2) NOT NULL,
        category TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        item TEXT NOT NULL,
        price NUMERIC(10,2) NOT NULL,
        qty INTEGER NOT NULL,
        date TEXT NOT NULL
    )
    """)

    db.commit()
    cur.close()
    db.close()

# ================= CART =================
def get_cart():
    return session.get("cart", {})

def save_cart(cart):
    session["cart"] = cart

# ================= عربي =================
def ar(text):
    return str(text)

# ================= ROUTES =================

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/invoice")
def invoice():
    db = connect()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM products ORDER BY id ASC")
    products = cur.fetchall()
    cur.close()
    db.close()

    food = [p for p in products if p["category"] == "food"]
    drinks = [p for p in products if p["category"] == "drink"]

    return render_template("invoice.html", food=food, drinks=drinks, cart=get_cart())

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    name = request.form["item"]
    price = float(request.form["price"])
    cart = get_cart()

    if name in cart:
        cart[name]["qty"] += 1
    else:
        cart[name] = {"price": price, "qty": 1}

    save_cart(cart)
    return redirect("/invoice")

@app.route("/update_qty", methods=["POST"])
def update_qty():
    name = request.form["name"]
    action = request.form["action"]
    cart = get_cart()

    if name in cart:
        if action == "plus":
            cart[name]["qty"] += 1
        elif action == "minus":
            cart[name]["qty"] -= 1
            if cart[name]["qty"] <= 0:
                del cart[name]

    save_cart(cart)
    return redirect("/invoice")

@app.route("/save")
def save():
    cart = get_cart()
    db = connect()
    cur = db.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    for item, data in cart.items():
        cur.execute(
            "INSERT INTO orders(item, price, qty, date) VALUES(%s, %s, %s, %s)",
            (item, data["price"], data["qty"], today)
        )

    db.commit()
    cur.close()
    db.close()
    session["cart"] = {}

    return redirect("/invoice?msg=saved")

# ================= PDF =================
@app.route("/print_pdf")
def print_pdf():
    cart = get_cart()

    try:
        pdfmetrics.registerFont(TTFont("Arabic", "Arial.ttf"))
        font_name = "Arabic"
    except:
        font_name = "Helvetica"

    doc = SimpleDocTemplate("invoice.pdf")

    arabic_style = ParagraphStyle(
        name="Arabic",
        fontName=font_name,
        fontSize=12,
        alignment=2
    )

    title_style = ParagraphStyle(
        name="TitleArabic",
        fontName=font_name,
        fontSize=16,
        alignment=1
    )

    data = [[
        Paragraph(ar("الصنف"), arabic_style),
        Paragraph(ar("الكمية"), arabic_style),
        Paragraph(ar("السعر"), arabic_style),
        Paragraph(ar("المجموع"), arabic_style)
    ]]

    total = 0

    for item, d in cart.items():
        line_total = d["qty"] * d["price"]
        total += line_total

        data.append([
            Paragraph(ar(item), arabic_style),
            Paragraph(str(d["qty"]), arabic_style),
            Paragraph(str(d["price"]), arabic_style),
            Paragraph(str(line_total), arabic_style)
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements = []
    elements.append(Paragraph(ar("MF Restaurant"), title_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(ar("07729981870"), arabic_style))
    elements.append(Spacer(1, 15))
    elements.append(table)
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(ar(f"المجموع الكلي: {total}"), arabic_style))

    doc.build(elements)

    return send_file("invoice.pdf", as_attachment=True)

# ================= REPORTS =================
@app.route("/reports")
def reports():
    return render_template("reports.html")

@app.route("/excel/<type>")
def excel(type):
    db = connect()

    if type == "day":
        days = 1
    elif type == "week":
        days = 7
    elif type == "month":
        days = 30
    else:
        db.close()
        return "خطأ"

    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    query = """
        SELECT item, qty, price, (qty * price) AS total, date
        FROM orders
        WHERE date >= %s
        ORDER BY id DESC
    """
    df = pd.read_sql_query(query, db, params=(start,))
    db.close()

    if df.empty:
        return "ماكو بيانات"

    file = f"report_{type}.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)

# ================= PRODUCTS =================
@app.route("/products")
def products():
    db = connect()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM products ORDER BY id DESC")
    products_data = cur.fetchall()
    cur.close()
    db.close()

    return render_template("products.html", products=products_data)

@app.route("/add_product", methods=["POST"])
def add_product():
    db = connect()
    cur = db.cursor()

    cur.execute(
        "INSERT INTO products(name, price, category) VALUES(%s, %s, %s)",
        (request.form["name"], request.form["price"], request.form["category"])
    )

    db.commit()
    cur.close()
    db.close()

    return redirect("/products")

@app.route("/delete_product/<id>")
def delete_product(id):
    db = connect()
    cur = db.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (id,))
    db.commit()
    cur.close()
    db.close()

    return redirect("/products")

# ================= RUN =================
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
