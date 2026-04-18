from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from datetime import datetime

app = Flask(__name__)

# ملفات البيانات
PRODUCTS_FILE = "products.xlsx"
INVOICES_FILE = "invoices.xlsx"

# تسجيل خط عربي إذا موجود
try:
    pdfmetrics.registerFont(TTFont("Arabic", "Arial.ttf"))
    FONT_NAME = "Arabic"
except:
    FONT_NAME = "Helvetica"


# =========================
# دالة العربي المعدلة
# =========================
def ar(text):
    return str(text)


# =========================
# الصفحة الرئيسية
# =========================
@app.route("/")
def home():
    return render_template("home.html")


# =========================
# المنتجات
# =========================
@app.route("/products", methods=["GET", "POST"])
def products():
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]

        if os.path.exists(PRODUCTS_FILE):
            df = pd.read_excel(PRODUCTS_FILE)
        else:
            df = pd.DataFrame(columns=["الاسم", "السعر"])

        df.loc[len(df)] = [name, price]
        df.to_excel(PRODUCTS_FILE, index=False)

        return redirect("/products")

    if os.path.exists(PRODUCTS_FILE):
        df = pd.read_excel(PRODUCTS_FILE)
        data = df.values.tolist()
    else:
        data = []

    return render_template("products.html", data=data)


# =========================
# الفاتورة
# =========================
@app.route("/invoice", methods=["GET", "POST"])
def invoice():
    if os.path.exists(PRODUCTS_FILE):
        df = pd.read_excel(PRODUCTS_FILE)
        products = df.values.tolist()
    else:
        products = []

    if request.method == "POST":
        customer = request.form["customer"]
        product = request.form["product"]
        qty = int(request.form["qty"])
        price = float(request.form["price"])
        total = qty * price
        date = datetime.now().strftime("%Y-%m-%d")

        if os.path.exists(INVOICES_FILE):
            df2 = pd.read_excel(INVOICES_FILE)
        else:
            df2 = pd.DataFrame(columns=["الزبون", "المنتج", "الكمية", "السعر", "المجموع", "التاريخ"])

        df2.loc[len(df2)] = [customer, product, qty, price, total, date]
        df2.to_excel(INVOICES_FILE, index=False)

        return redirect("/invoice")

    return render_template("invoice.html", products=products)


# =========================
# التقارير
# =========================
@app.route("/reports")
def reports():
    if os.path.exists(INVOICES_FILE):
        df = pd.read_excel(INVOICES_FILE)
        data = df.values.tolist()
        total_sales = df["المجموع"].sum()
    else:
        data = []
        total_sales = 0

    return render_template("reports.html", data=data, total_sales=total_sales)


# =========================
# PDF
# =========================
@app.route("/pdf")
def pdf():
    file_name = "report.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    c.setFont(FONT_NAME, 16)

    c.drawString(200, 800, ar("تقرير المبيعات"))

    if os.path.exists(INVOICES_FILE):
        df = pd.read_excel(INVOICES_FILE)
        y = 760

        for i, row in df.iterrows():
            line = f"{row['الزبون']} - {row['المجموع']}"
            c.drawString(50, y, ar(line))
            y -= 25

    c.save()

    return send_file(file_name, as_attachment=True)


# =========================
# تشغيل البرنامج
# =========================
if __name__ == "__main__":
    app.run(debug=True)
