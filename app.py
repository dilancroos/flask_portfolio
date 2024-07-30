import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from markupsafe import escape
from datetime import date

from helpers import apology, login_required, lookup, usd, manager_required, admin_required

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///hotel.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    return render_template("index.html")


@app.route("/rooms", methods=["GET"])
@login_required
def rooms():
    """Show rooms"""

    # Get current user
    user = db.execute(
        "SELECT * FROM staff_members WHERE staffID = ?", session["user_id"])

    rooms = db.execute(
        "SELECT rooms.roomID, hotels.name as hotelName , roomTypes.name as roomTypeName, rooms.roomNo, status.status FROM rooms INNER JOIN hotels ON rooms.hotelID = hotels.hotelID INNER JOIN roomTypes ON rooms.typeID = roomTypes.typeID INNER JOIN status ON rooms.statusID = status.statusID WHERE hotels.hotelID = ? ORDER BY roomTypeName ASC, roomNo ASC", user[0]["hotelID"])

    return render_template("rooms.html", rooms=rooms)


@app.route("/bookings", methods=["GET"])
@login_required
def bookings():
    """Show bookings"""

    bookings = db.execute(
        "SELECT bookings.*, guests.firstName, guests.lastName, rooms.roomNo, mealPlans.name as mealPlanName, status.status FROM bookings INNER JOIN rooms ON bookings.roomID = rooms.roomID INNER JOIN guests ON bookings.guestID = guests.guestID INNER JOIN mealPlans ON bookings.mealPlanID = mealPlans.mealPlanID INNER JOIN status ON bookings.statusID = status.statusID WHERE rooms.hotelID = ? ORDER BY checkInDate, checkOutDate", session["hotelID"])

    return render_template("bookings.html", bookings=bookings)


@app.route("/guests", methods=["GET"])
@login_required
def guests():
    """Show guests"""

    guests = db.execute(
        "SELECT guests.*, identityDocs.name as idTypeName, countries.en_short_name as country FROM guests INNER JOIN identityDocs ON guests.idType = identityDocs.idID INNER JOIN countries ON guests.countryID = countries.num_code WHERE guestID >= 1 ORDER BY firstName, lastName, dateOfBirth")

    return render_template("guests.html", guests=guests)


@app.route("/hotels", methods=["GET"])
@manager_required
def hotels():
    """Show hotels"""

    hotels = db.execute(
        "SELECT hotels.*, status.status FROM hotels INNER JOIN status ON hotels.statusID = status.statusID")

    return render_template("hotels.html", hotels=hotels)


@app.route("/roomTypes", methods=["GET"])
@manager_required
def roomTypes():
    """Show room types"""

    roomTypes = db.execute(
        "SELECT roomTypes.*, status.status FROM roomTypes INNER JOIN status ON roomTypes.statusID = status.statusID ORDER BY capacity ASC")

    return render_template("roomTypes.html", roomTypes=roomTypes)


@app.route("/staff", methods=["GET"])
@manager_required
def staff():
    """Show staff"""

    staff = db.execute(
        "SELECT staff_members.*, hotels.name as hotelName, status.status, position.name as position FROM staff_members INNER JOIN hotels ON staff_members.hotelID = hotels.hotelID INNER JOIN status ON staff_members.statusID = status.statusID INNER JOIN position ON staff_members.positionID = position.id ORDER BY positionID DESC, firstName, lastName")

    return render_template("staff.html", staff=staff)


@app.route("/mealPlans", methods=["GET"])
@manager_required
def mealPlans():
    """Show meal plans"""

    mealPlans = db.execute(
        "SELECT mealPlans.*, status.status FROM mealPlans INNER JOIN status ON mealPlans.statusID = status.statusID")

    return render_template("mealPlans.html", mealPlans=mealPlans)


@app.route("/new_room", methods=["GET", "POST"])
@manager_required
def new_room():
    """Add new room"""

    if request.method == "POST":
        hotelID = request.form.get("hotelID")
        roomTypeID = request.form.get("roomTypeID")
        roomNo = request.form.get("roomNo")
        statusID = request.form.get("statusID")

        if db.execute("INSERT INTO rooms (hotelID, typeID, roomNo, status) VALUES (?, ?, ?, ?)",
                      hotelID, roomTypeID, roomNo, statusID):
            flash("Room added successfully")
        else:
            flash("Room add failed")

        return redirect("/rooms")

    hotels = db.execute(
        "SELECT * FROM hotels WHERE statusID = 1")

    roomTypes = db.execute(
        "SELECT * FROM roomTypes WHERE statusID = 1")

    allStatus = db.execute(
        "SELECT * FROM status")

    return render_template("new_room.html", roomTypes=roomTypes, hotels=hotels, allStatus=allStatus)


@app.route("/edit_room", methods=["GET", "POST"])
@manager_required
def edit_room():
    """Edit room"""

    if request.method == "POST":
        roomID = request.form.get("roomid")
        hotelID = request.form.get("hotelID")
        roomTypeID = request.form.get("roomTypeID")
        roomNo = request.form.get("roomNo")
        statusID = request.form.get("statusID")

        # Update room information using parameterized query
        if db.execute("""UPDATE rooms SET hotelID = ?, typeID = ?, roomNo = ?, statusID = ? WHERE roomID = ?""",
                      hotelID, roomTypeID, roomNo, statusID, roomID):

            # Check if the update was successful
            flash("Room updated successfully")
        else:
            flash("Room update failed")

        return redirect("/rooms")

    roomid = request.args.get("roomid", type=int)
    room = db.execute("SELECT * FROM rooms WHERE roomID = ?", roomid)

    # Fetch the room details, hotels, room types, and status options
    room = room[0] if room else None
    hotels = db.execute("SELECT * FROM hotels WHERE statusID = 1")
    roomTypes = db.execute("SELECT * FROM roomTypes WHERE statusID = 1")
    allStatus = db.execute("SELECT * FROM status")

    return render_template("edit_room.html", room=room, roomTypes=roomTypes, hotels=hotels, allStatus=allStatus)


@app.route("/new_guest", methods=["GET", "POST"])
@login_required
def new_guest():
    """Add new guest"""

    if request.method == "POST":
        firstName = request.form.get("firstName")
        lastName = request.form.get("lastName")
        dateOfBirth = request.form.get("dateOfBirth")
        address = request.form.get("address")
        country = request.form.get("country")
        phone = request.form.get("phone")
        email = request.form.get("email")
        idType = request.form.get("idType")
        idNumber = request.form.get("idNumber")

        if db.execute("INSERT INTO guests (firstName, lastName, dateOfBirth, address, countryID, phone, email, idType, idNumber) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      firstName, lastName, dateOfBirth, address, country, phone, email, idType, idNumber):
            flash("Guest added successfully")
        else:
            flash("Guest add failed")

        return redirect("/guests")

    idTypes = db.execute(
        "SELECT * FROM identityDocs")
    countires = db.execute(
        "SELECT * FROM countries")

    return render_template("new_guest.html", idTypes=idTypes, countires=countires)


@app.route("/edit_guest", methods=["GET", "POST"])
@manager_required
def edit_guest():
    """Edit guest"""

    if request.method == "POST":
        guestID = request.form.get("guestid")
        firstName = request.form.get("firstName")
        lastName = request.form.get("lastName")
        dateOfBirth = request.form.get("dateOfBirth")
        address = request.form.get("address")
        countryID = request.form.get("country")
        phone = request.form.get("phone")
        email = request.form.get("email")
        idType = request.form.get("idType")
        idNumber = request.form.get("idNumber")

        # Update guest information using parameterized query
        if db.execute("""UPDATE guests SET firstName = ?, lastName = ?, dateOfBirth = ?, address = ?, countryID = ?, phone = ?, email = ?, idType = ?, idNumber = ? WHERE guestID = ?""",
                      firstName, lastName, dateOfBirth, address, countryID, phone, email, idType, idNumber, guestID):

            # Check if the update was successful
            flash("Guest updated successfully")
        else:
            flash("Guest update failed")

        return redirect("/guests")

    guestID = request.args.get("guestid", type=int)
    guest = db.execute("SELECT * FROM guests WHERE guestID = ?", guestID)

    # Fetch the guest details, id types, and countries
    guest = guest[0] if guest else None
    idTypes = db.execute("SELECT * FROM identityDocs")
    countires = db.execute("SELECT * FROM countries")

    return render_template("edit_guest.html", guest=guest, idTypes=idTypes, countires=countires)


@app.route("/guest_bookings", methods=["GET"])
@login_required
def guest_bookings():
    """Show guest bookings"""

    guestID = request.args.get("guestid", type=int)

    guest = db.execute(
        "SELECT * FROM guests WHERE guestID = ?", guestID)

    bookings = db.execute(
        "SELECT bookings.*, rooms.roomNo, mealPlans.name as mealPlanName, status.status FROM bookings INNER JOIN rooms ON bookings.roomID = rooms.roomID INNER JOIN mealPlans ON bookings.mealPlanID = mealPlans.mealPlanID INNER JOIN status ON bookings.statusID = status.statusID WHERE guestID = ? ORDER BY checkInDate", guestID)

    # send the number of nights for each booking handling "ValueError: invalid literal for int() with base 10: '2024-07-25'" error
    totalNights = 0
    for booking in bookings:
        try:
            # get
            checkInDate = date(int(booking["checkInDate"].split("-")[0]), int(
                booking["checkInDate"].split("-")[1]), int(booking["checkInDate"].split("-")[2]))
            checkOutDate = date(int(booking["checkOutDate"].split("-")[0]), int(
                booking["checkOutDate"].split("-")[1]), int(booking["checkOutDate"].split("-")[2]))
            booking["nights"] = (checkOutDate - checkInDate).days
            totalNights += booking["nights"]
        except ValueError:
            booking["nights"] = "oops"

    return render_template("guest_bookings.html", guest=guest, bookings=bookings, totalNights=totalNights)


@app.route("/delete_guest", methods=["GET"])
@admin_required
def delete_guest():
    """Delete guest"""

    guestID = request.args.get("guestid")

    try:
        if db.execute("DELETE FROM guests WHERE guestID = ?", guestID):
            flash("Guest deleted successfully")
        else:
            flash("Guest delete failed")
    except:
        bookings = db.execute(
            "SELECT * FROM bookings WHERE guestID = ?", guestID)

        if bookings:
            db.execute(
                "UPDATE bookings SET guestID = ? WHERE guestID = ?", 0, guestID)
            db.execute("DELETE FROM guests WHERE guestID = ?", guestID)
            flash(
                "Guests bookings reassigned to 'Unknown' and guest deleted successfully")

    return redirect("/guests")


@app.route("/new_booking", methods=["GET", "POST"])
@login_required
def new_booking():
    """Add new booking"""

    if request.method == "POST":
        guestID = request.form.get("guestID")
        roomID = request.form.get("roomID")
        checkInDate = request.form.get("checkIn")
        checkOutDate = request.form.get("checkOut")
        mealPlanID = request.form.get("mealPlan")

        checkInDateV = date(int(checkInDate.split("-")[0]), int(
            checkInDate.split("-")[1]), int(checkInDate.split("-")[2]))
        checkOutDateV = date(int(checkOutDate.split("-")[0]), int(
            checkOutDate.split("-")[1]), int(checkOutDate.split("-")[2]))

        # Check if check-in date is before check-out date
        if checkInDateV > checkOutDateV:
            flash("Check-in date should be before check-out date")
            return redirect("/new_booking")

        # Check if room is available
        room = db.execute("SELECT * FROM bookings WHERE roomID = ? AND ((checkInDate <= ? AND checkOutDate >= ?) OR (checkInDate <= ? AND checkOutDate >= ?) OR (checkInDate >= ? AND checkOutDate <= ?))",
                          roomID, checkInDate, checkInDate, checkOutDate, checkOutDate, checkInDate, checkOutDate)
        if room:
            flash("Room is not available for the selected dates")
            return redirect("/new_booking")

        # Check if check-in date is before today
        if checkInDateV < date.today():
            flash("Check-in date should be today or later")
            return redirect("/new_booking")

        # Check if check-in date is more than 1 year in the future
        if checkInDateV > date.today().replace(year=date.today().year + 1):
            flash("Check-in date should be within the next 1 year")
            return redirect("/new_booking")

        if db.execute("INSERT INTO bookings (guestID, roomID, checkInDate, checkOutDate, mealPlanID, statusID) VALUES (?, ?, ?, ?, ?, ?)",
                      guestID, roomID, checkInDate, checkOutDate, mealPlanID, 1):
            flash("Booking added successfully")
        else:
            flash("Booking add failed")

        return redirect("/bookings")

    guestID = request.args.get("guestid", type=int)

    if guestID:
        guests = db.execute(
            "SELECT * FROM guests WHERE guestID = ?", guestID)
    else:
        guests = db.execute(
            "SELECT * FROM guests WHERE guestID >= 1")  # get all guests with guestID >= 1

    rooms = db.execute(
        "SELECT rooms.roomID, hotels.name as hotelName , roomTypes.name as roomTypeName, rooms.roomNo, status.status FROM rooms INNER JOIN hotels ON rooms.hotelID = hotels.hotelID INNER JOIN roomTypes ON rooms.typeID = roomTypes.typeID INNER JOIN status ON rooms.statusID = status.statusID WHERE hotels.hotelID = ? ORDER BY roomTypeName ASC, roomNo ASC", session["hotelID"])

    mealPlans = db.execute(
        "SELECT * FROM mealPlans WHERE statusID = 1")

    allStatus = db.execute(
        "SELECT * FROM status")

    return render_template("new_booking.html", guests=guests, rooms=rooms, mealPlans=mealPlans, allStatus=allStatus, gGetID=guestID)


@app.route("/edit_booking", methods=["GET", "POST"])
@login_required
def edit_booking():
    """Edit booking"""

    if request.method == "POST":
        bookingID = request.form.get("bookingid")
        guestID = request.form.get("guestID")
        roomID = request.form.get("roomID")
        checkInDate = request.form.get("checkIn")
        checkOutDate = request.form.get("checkOut")
        mealPlanID = request.form.get("mealPlan")
        statusID = request.form.get("statusID")

        checkInDateV = date(int(checkInDate.split("-")[0]), int(
            checkInDate.split("-")[1]), int(checkInDate.split("-")[2]))
        checkOutDateV = date(int(checkOutDate.split("-")[0]), int(
            checkOutDate.split("-")[1]), int(checkOutDate.split("-")[2]))

        # Check if check-in date is before check-out date
        if checkInDateV > checkOutDateV:
            flash("Check-in date should be before check-out date")
            return redirect("/edit_booking")

        # Check if room is available
        room = db.execute("SELECT * FROM bookings WHERE roomID = ? AND ((checkInDate <= ? AND checkOutDate >= ?) OR (checkInDate <= ? AND checkOutDate >= ?) OR (checkInDate >= ? AND checkOutDate <= ?)) AND bookingID != ?",
                          roomID, checkInDate, checkInDate, checkOutDate, checkOutDate, checkInDate, checkOutDate, bookingID)
        if room:
            flash("Room is not available for the selected dates")
            return redirect("/edit_booking")

        # Check if check-in date is before today
        if checkInDateV < date.today():
            flash("Check-in date should be today or later")
            return redirect("/edit_booking")

        # Check if check-in date is more than 1 year in the future
        if checkInDateV > date.today().replace(year=date.today().year + 1):
            flash("Check-in date should be within the next 1 year")
            return redirect("/edit_booking")

        # Update booking information using parameterized query
        if db.execute("""UPDATE bookings SET guestID = ?, roomID = ?, checkInDate = ?, checkOutDate = ?, mealPlanID = ?, statusID = ? WHERE bookingID = ?""",
                      guestID, roomID, checkInDate, checkOutDate, mealPlanID, statusID, bookingID):

            # Check if the update was successful
            flash("Booking updated successfully")
        else:
            flash("Booking update failed")

        return redirect("/bookings")

    bookingID = request.args.get("bookingid")
    booking = db.execute(
        "SELECT * FROM bookings WHERE bookingID = ?", bookingID)

    # Fetch the booking details, guests, rooms, meal plans, and statusID options
    booking = booking[0] if booking else None
    guests = db.execute("SELECT * FROM guests")
    rooms = db.execute(
        "SELECT rooms.roomID, hotels.name as hotelName , roomTypes.name as roomTypeName, rooms.roomNo, status.status FROM rooms INNER JOIN hotels ON rooms.hotelID = hotels.hotelID INNER JOIN roomTypes ON rooms.typeID = roomTypes.typeID INNER JOIN status ON rooms.statusID = status.statusID WHERE hotels.hotelID = ? ORDER BY roomTypeName ASC, roomNo ASC", session["hotelID"])
    mealPlans = db.execute("SELECT * FROM mealPlans WHERE statusID = 1")
    allStatus = db.execute("SELECT * FROM status")

    return render_template("edit_booking.html", booking=booking, guests=guests, rooms=rooms, mealPlans=mealPlans, allStatus=allStatus)


@app.route("/edit_hotel", methods=["GET", "POST"])
@manager_required
def edit_hotel():
    """Edit hotel"""

    if request.method == "POST":
        hotelID = request.form.get("hotelid")
        name = request.form.get("name")
        address = request.form.get("address")
        phone = request.form.get("phone")
        email = request.form.get("email")
        statusID = request.form.get("status")

        # Update hotel information using parameterized query
        if db.execute("""UPDATE hotels SET name = ?, address = ?, phone = ?, email = ?, statusID = ? WHERE hotelID = ?""",
                      name, address, phone, email, statusID, hotelID):

            # Check if the update was successful
            flash("Hotel updated successfully")
        else:
            flash("Hotel update failed")

        return redirect("/hotels")

    hotelID = request.args.get("hotelid")
    hotel = db.execute("SELECT * FROM hotels WHERE hotelID = ?", hotelID)

    # Fetch the hotel details and status options
    hotel = hotel[0] if hotel else None
    allStatus = db.execute("SELECT * FROM status")

    return render_template("edit_hotel.html", hotel=hotel, allStatus=allStatus)


@app.route("/new_hotel", methods=["GET", "POST"])
@admin_required
def new_hotel():
    """Add new hotel"""

    if request.method == "POST":
        name = request.form.get("name")
        address = request.form.get("address")
        phone = request.form.get("phone")
        email = request.form.get("email")
        checkinTime = request.form.get("checkinTime")
        checkoutTime = request.form.get("checkoutTime")
        statusID = request.form.get("status")

        if db.execute("INSERT INTO hotels (name, address, phone, email, checkinTime, checkoutTime,statusID) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      name, address, phone, email, checkinTime, checkoutTime, statusID):
            flash("Hotel added successfully")
        else:
            flash("Hotel add failed")

        return redirect("/hotels")

    allStatus = db.execute(
        "SELECT * FROM status")

    return render_template("new_hotel.html", allStatus=allStatus)


@app.route("/edit_roomType", methods=["GET", "POST"])
@admin_required
def edit_roomType():
    """Edit room type"""

    if request.method == "POST":
        typeID = request.form.get("typeid")
        name = request.form.get("name")
        capacity = request.form.get("capacity")
        description = request.form.get("description")
        price = request.form.get("price")
        statusID = request.form.get("status")

        # Update room type information using parameterized query
        if db.execute("""UPDATE roomTypes SET name = ?, capacity = ?, description = ?, statusID = ? WHERE typeID = ?""",
                      name, capacity, description, price, statusID, typeID):

            # Check if the update was successful
            flash("Room type updated successfully")
        else:
            flash("Room type update failed")

        return redirect("/roomTypes")

    typeID = request.args.get("typeid")
    roomType = db.execute("SELECT * FROM roomTypes WHERE typeID = ?", typeID)

    # Fetch the room type details and status options
    roomType = roomType[0] if roomType else None
    allStatus = db.execute("SELECT * FROM status")

    return render_template("edit_roomType.html", roomType=roomType, allStatus=allStatus)


@app.route("/new_staff", methods=["GET", "POST"])
@manager_required
def new_staff():
    """Add new staff"""

    if request.method == "POST":
        firstName = request.form.get("firstName")
        lastName = request.form.get("lastName")
        phone = request.form.get("phone")
        email = request.form.get("email")
        hotelID = request.form.get("hotel")
        statusID = request.form.get("status")
        positionID = request.form.get("position")
        dob = request.form.get("dateOfBirth")
        password = request.form.get("password")
        conPassword = request.form.get("confirmPassword")

        # if less than 18 years old
        if date.today().year - int(dob.split("-")[0]) < 18:
            flash("Staff should be at least 18 years old")
            return redirect("/new_staff")

        # if password and confirm password do not match
        if password != conPassword:
            flash("Passwords do not match")
            return redirect("/new_staff")

        if db.execute("INSERT INTO staff_members (firstName, lastName, positionID, dateOfBirth, phone, email, hotelID, statusID, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      firstName, lastName, positionID, dob, phone, email, hotelID, statusID, generate_password_hash(password, method='pbkdf2', salt_length=16)):
            flash("Staff added successfully")
        else:
            flash("Staff add failed")

        return redirect("/staff")

    hotels = db.execute(
        "SELECT * FROM hotels")
    allStatus = db.execute(
        "SELECT * FROM status")
    positions = db.execute(
        "SELECT * FROM position")

    return render_template("new_staff.html", hotels=hotels, allStatus=allStatus, positions=positions)


@app.route("/edit_staff", methods=["GET", "POST"])
@admin_required
def edit_staff():
    """Edit staff"""

    if request.method == "POST":
        staffID = request.form.get("staffid")
        firstName = request.form.get("firstName")
        lastName = request.form.get("lastName")
        phone = request.form.get("phone")
        email = request.form.get("email")
        hotelID = request.form.get("hotel")
        statusID = request.form.get("status")

        # Update staff information using parameterized query
        if db.execute("""UPDATE staff_members SET firstName = ?, lastName = ?, phone = ?, email = ?, hotelID = ?, statusID = ? WHERE staffID = ?""",
                      firstName, lastName, phone, email, hotelID, statusID, staffID):

            # Check if the update was successful
            flash("Staff updated successfully")
        else:
            flash("Staff update failed")

        return redirect("/staff")

    staffID = request.args.get("staffid")
    staff = db.execute(
        "SELECT staff_members.*, position.name as position FROM staff_members INNER JOIN position ON position.id = staff_members.positionID WHERE staffID = ?", staffID)

    # Fetch the staff details, hotels, and status options
    staff = staff[0] if staff else None
    hotels = db.execute("SELECT * FROM hotels")
    allStatus = db.execute("SELECT * FROM status")
    positions = db.execute("SELECT * FROM position")

    return render_template("edit_staff.html", staff=staff, hotels=hotels, allStatus=allStatus, positions=positions)


@ app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM staff_members WHERE firstName = ?", request.form.get(
            "username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["staffID"]
        session["username"] = rows[0]["firstName"]
        session["positionID"] = rows[0]["positionID"]
        session["hotelID"] = rows[0]["hotelID"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@ app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@ app.route("/changepw", methods=["GET", "POST"])
@ login_required
def changePassword():
    """Change password"""

    msg = False

    if request.method == "POST":

        # Ensure old password was submitted
        if not request.form.get("oldpassword"):
            return apology("must provide old password", 403)

        # Ensure new password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure confirm password was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password conformation", 403)

        if (request.form.get("password") != request.form.get("confirmation")):
            return apology("Passwords dont match", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE id = ?", session["user_id"]
        )

        # Check old password matches logged in user
        if check_password_hash(rows[0]["hash"], request.form.get("oldpassword")):
            db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(
                request.form.get("password"), method='pbkdf2', salt_length=16), session["user_id"])

            msg = True
        else:
            return apology("Old password does not match", 403)

    return render_template("changepw.html", msg=msg)


"""
For the completion of the project I used the following resources:
- https://flask.palletsprojects.com/en/3.0.x/
- https://sqlite.org/index.html
- https://www.sqlitetutorial.net
- https://getbootstrap.com/docs/5.3/getting-started/introduction/
- https://www.w3schools.com
- https://stackoverflow.com
- https://www.youtube.com
- https://www.google.com
- https://www.cs50.io
- https://www.github.com

Some inspiration for the hotel management system was taken from the following link:
https://vertabelo.com/blog/data-model-for-hotel-management-system/

The Country Codes and Names were taken from the following link:
https://github.com/Imagin-io/country-nationality-list/blob/master/countries.sql

Readme file was created using the following link:
https://github.com/othneildrew/Best-README-Template

I aslo used GitHub Copilot for some of the code snippets
and ChatGPT for some debugging and code suggestions

If I have missed any resources, please let me know and I will add them to the list
"""
