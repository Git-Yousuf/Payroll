from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import mysql.connector
from datetime import datetime
from openpyxl import Workbook, load_workbook
import io

app = Flask(__name__)
app.secret_key = "zxcvbnm951"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="payroll"
)

# ---------- STAFF CODE GENERATOR ----------
def generate_staff_code(cursor, department, date_of_join):
    dept_codes = {
        "ENGLISH": "01", "TAMIL": "02", "ARABIC": "03", "URDU": "04",
        "HINDI": "05", "FRENCH": "06", "HISTORICAL STUDIES": "07",
        "ECONOMICS": "08", "SOCIOLOGY": "09", "COMMERCE": "10",
        "CORPORATE SECRETARYSHIP": "11", "MATHEMATICS": "12",
        "PHYSICS": "13", "CHEMISTRY": "14", "BOTANY": "15",
        "ZOOLOGY": "16", "COMPUTER SCIENCE": "17",
        "COMPUTER APPLICATION": "18", "INFORMATION SYSTEM MANAGEMENT": "19",
        "BUSINESS ADMIN": "20", "BANK MANAGEMENT": "21",
        "BIOTECHNOLOGY": "22", "INFORMATION TECHNOLOGY": "23",
        "ACCOUNTS & FINANCE": "24",
        "CRIMINOLOGY & POLICE ADMINISTRATION": "25",
        "DEFENCE & STRATEGIC STUDIES": "26",
        "ELECTRONIC MEDIA": "27", "PROFESSIONAL ACCOUNTING": "28",
        "ARTIFICIAL INTELLIGENCE": "29", "DATASCIENCE": "30", "PHYSICAL EDUCATION": "31",
        "LIBRARY": "32"
    }

    dept_code = dept_codes[department.upper()]
    year_code = str(date_of_join.year)[-2:]

    cursor.execute(
        "SELECT COUNT(*) AS series FROM employees WHERE staff_code LIKE %s",
        (f"{year_code}{dept_code}%",)
    )
    row = cursor.fetchone()
    series = (row["series"] or 0) + 1

    return f"{year_code}{dept_code}{series:03}"


# ---------- INDEX ----------
@app.route("/")
def index():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    cursor.close()
    return render_template("index.html", employees=employees)


# ---------- ADD EMPLOYEE ----------
@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    if request.method == "POST":
        cursor = db.cursor(dictionary=True)
        try:
            doj_str = request.form["date_of_join"]
            doj = datetime.strptime(doj_str, "%Y-%m-%d").date()

            staff_code = generate_staff_code(
                cursor,
                request.form["department"],
                doj
            )

            values = (
                staff_code,
                request.form["name"],
                request.form["department"],
                request.form["designation"],
                request.form["category"],
                request.form.get("aadhar"),
                request.form.get("pan"),
                request.form.get("bank_account"),
                request.form.get("pf_account"),
                request.form.get("basic", 0),
                request.form.get("hra", 0),
                request.form.get("da", 0),
                request.form.get("cca", 0),
                request.form.get("ir", 0),
                request.form.get("ma", 0),
                request.form.get("special_allowance", 0),
                doj_str,
                request.form.get("dob"),
                request.form.get("esi", 0),
                request.form.get("insurance", 0),
                request.form.get("pf", 0),
                request.form.get("professional_tax", 0),
                request.form.get("teachers_guild", 0),
                request.form.get("ntsw", 0),
                request.form.get("icrs", 0),
                request.form.get("ncswp", 0),
                request.form.get("nta", 0),
                request.form.get("gross_salary", 0),
                request.form.get("total_deductions", 0),
                request.form.get("net_salary", 0),
                request.form.get("phone"),
                request.form.get("email"),
                request.form.get("increment_month"),
            )

            cursor.execute("""
                INSERT INTO employees
                (staff_code, name, department, designation, category,
                 aadhar, pan, bank_account, pf_account,
                 basic, hra, da, cca, ir, ma, special_allowance,
                 date_of_join, dob,
                 esi, insurance, pf, professional_tax, teachers_guild,
                 ntsw, icrs, ncswp, nta,
                 gross_salary, total_deductions, net_salary,
                 phone, email, increment_month)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s)
            """, values)

            db.commit()
            flash("Employee Added Successfully ✅", "success")

        except Exception as e:
            flash(str(e), "error")
        finally:
            cursor.close()

        return redirect(url_for("add_employee"))

    return render_template("add_employee.html")


# ---------- DOWNLOAD TEMPLATE ----------
@app.route("/download_employee_template")
def download_employee_template():
    cursor = db.cursor()
    cursor.execute("DESCRIBE employees")

    columns = [
        r[0] for r in cursor.fetchall()
        if r[0] not in ("id", "staff_code", "created_at", "updated_at")
    ]
    cursor.close()

    wb = Workbook()
    ws = wb.active
    ws.append(columns)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    return send_file(
        stream,
        as_attachment=True,
        download_name="employee_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------- UPLOAD EXCEL ----------
@app.route("/upload_employee_excel", methods=["POST"])
def upload_employee_excel():
    file = request.files.get("excel_file")
    if not file:
        flash("No file selected ❌", "error")
        return redirect(url_for("index"))

    wb = load_workbook(file)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    headers = [h for h in rows[0] if h]
    data_rows = rows[1:]

    cursor = db.cursor(dictionary=True)

    for row in data_rows:
        if all(v is None for v in row):
            continue

        data = dict(zip(headers, row))
        doj = data["date_of_join"]
        if isinstance(doj, str):
            doj = datetime.strptime(doj, "%Y-%m-%d").date()

        staff_code = generate_staff_code(cursor, data["department"], doj)

        cols = ["staff_code"] + list(data.keys())
        vals = [staff_code] + list(data.values())

        placeholders = ",".join(["%s"] * len(vals))
        cursor.execute(
            f"INSERT INTO employees ({','.join(cols)}) VALUES ({placeholders})",
            vals
        )

    db.commit()
    cursor.close()
    flash("Employees uploaded successfully ✅", "success")
    return redirect(url_for("index"))

@app.route("/delete_employee/<staff_code>", methods=["POST"])
def delete_employee(staff_code):
    cursor = db.cursor()
    try:
        cursor.execute(
            "DELETE FROM employees WHERE staff_code = %s",
            (staff_code,)
        )
        db.commit()
        flash(f"Employee {staff_code} deleted successfully 🗑️", "success")
    except Exception as e:
        flash(str(e), "error")
    finally:
        cursor.close()

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)

