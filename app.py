
from flask import Flask, render_template, request, redirect, url_for
from database import init_db, get_connection
from ai_service import generate_health_remarks
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
import math

app = Flask(__name__)

init_db()


def validate_patient_form(form):
    full_name = form.get("full_name", "").strip()
    dob = form.get("dob", "").strip()
    email = form.get("email", "").strip()

    if not full_name or len(full_name) > 100:
        return None, "Enter a name of 1 to 100 characters."

    try:
        dob_date = datetime.strptime(dob, "%d/%m/%Y").date()

        if dob_date.strftime("%d/%m/%Y") != dob:
            return None, "Enter a valid date in DD/MM/YYYY format."

        if dob_date > datetime.today().date():
            return None, "Date of birth cannot be in the future."

    except ValueError:
        return None, "Enter a valid date in DD/MM/YYYY format."

    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        return None, "Enter a valid email address."

    try:
        glucose = float(form.get("glucose", ""))
        haemoglobin = float(form.get("haemoglobin", ""))
        cholesterol = float(form.get("cholesterol", ""))

        values = [glucose, haemoglobin, cholesterol]

        if any(not math.isfinite(value) or value < 0 for value in values):
            return None, "Measurements must be finite, non-negative numbers."

    except (ValueError, TypeError):
        return None, "Enter valid numeric measurements."

    return {
        "full_name": full_name,
        "dob": dob,
        "email": email,
        "glucose": glucose,
        "haemoglobin": haemoglobin,
        "cholesterol": cholesterol,
    }, None


@app.route("/")
def home():
    connection = get_connection()
    patients = connection.execute(
        "SELECT * FROM patients ORDER BY id DESC"
    ).fetchall()
    connection.close()

    return render_template("index.html", patients=patients)


@app.route("/add", methods=["POST"])
def add_patient():
    patient, error = validate_patient_form(request.form)

    if error:
        return error, 400

    remarks = generate_health_remarks(patient)

    connection = get_connection()
    connection.execute(
        """
        INSERT INTO patients
        (full_name, dob, email, glucose, haemoglobin, cholesterol, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient["full_name"],
            patient["dob"],
            patient["email"],
            patient["glucose"],
            patient["haemoglobin"],
            patient["cholesterol"],
            remarks,
        ),
    )
    connection.commit()
    connection.close()

    return redirect(url_for("home"))


@app.route("/edit/<int:patient_id>", methods=["GET", "POST"])
def edit_patient(patient_id):
    connection = get_connection()

    patient = connection.execute(
        "SELECT * FROM patients WHERE id = ?",
        (patient_id,),
    ).fetchone()

    if patient is None:
        connection.close()
        return "Patient record not found.", 404

    if request.method == "POST":
        updated, error = validate_patient_form(request.form)

        if error:
            connection.close()
            return error, 400

        remarks = generate_health_remarks(updated)

        connection.execute(
            """
            UPDATE patients
            SET full_name = ?, dob = ?, email = ?, glucose = ?,
                haemoglobin = ?, cholesterol = ?, remarks = ?
            WHERE id = ?
            """,
            (
                updated["full_name"],
                updated["dob"],
                updated["email"],
                updated["glucose"],
                updated["haemoglobin"],
                updated["cholesterol"],
                remarks,
                patient_id,
            ),
        )

        connection.commit()
        connection.close()

        return redirect(url_for("home"))

    connection.close()

    return render_template("edit.html", patient=patient)


@app.route("/delete/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    connection = get_connection()

    connection.execute(
        "DELETE FROM patients WHERE id = ?",
        (patient_id,),
    )

    connection.commit()
    connection.close()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
