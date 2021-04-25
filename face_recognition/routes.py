from flask import Flask, render_template, Blueprint, request, redirect, url_for, current_app,flash,session,logging
from face_recognition import app,db,bcrypt
from face_recognition.database import Student,TimeTable,Attendence,user
from face_recognition.forms import RegisterForm,AddTimeTableForm, UserRegistrationForm, UserLoginForm
from flask_login import logout_user,LoginManager,UserMixin,login_required,login_user,current_user
from werkzeug.utils import secure_filename
import os
from pathlib import Path
from face_recognition.WebCam_Face_Recognition import modules
from flask_bcrypt import Bcrypt
import bcrypt
from face_recognition.WebCam_Face_Recognition import LiveFaceRecognition
from datetime import datetime
import numpy as np
import datetime as dt
from functools import wraps

#face images folder
app.config['UPLOAD_FOLDER'] = "./face_recognition/8_5-Dataset/train"
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'heic', 'jpeg', 'gif',''}

def allowed_file(file):
    temp = file[::-1]
    if '.' not in file:
        return False
    extension = temp[:temp.index('.')][::-1]
    print(extension)
    if extension.lower() in ALLOWED_EXTENSIONS:
        return True
    return False

def student_login_required(page):
    @wraps(page)
    def wrap(*args,**kwargs):
        if current_user.is_authenticated:
            if current_user.type == "student":
                return page(*args,**kwargs)
            else:
                flash("you need to login first as student!", "danger")
                logout_user()
                return redirect(url_for("userlogin"))
        else:
            flash("you need to login first","danger")
            return redirect(url_for("userlogin"))
    return wrap

def faculty_login_required(page):
    @wraps(page)
    def wrap(*args,**kwargs):
        if current_user.is_authenticated:
            if current_user.type == "faculty":
                return page(*args,**kwargs)
            else:
                flash("you need to login first as faculty!", "danger")
                logout_user()
                return redirect(url_for("login_faculty"))
        else:
            flash("you need to login first","danger")
            return redirect(url_for("userlogin"))
    return wrap

@app.route("/")
@app.route("/home")
def home():
    db.create_all()
    #print(data)
    return render_template("index.html")

@app.route("/faculty-home")
def facultyhome():
    db.create_all()
    #print(data)
    return render_template("Admin/index.html")

@app.route("/add-lecture", methods=["POST","GET"])
@faculty_login_required
def timetable():
    print(current_user)
    if request.method == "POST":
        sub = request.form["subject"]
        name = request.form["first_name"]
        sem = request.form["sem"][0]
        batch = request.form["batch"]
        slot = request.form["slot"][0]
        faculty_id = request.form["faculty_id"]

        if sum == "" or name == "" or sem == "" or batch=="" or slot=="":
            flash("enter all data","danger")
            return redirect(url_for("timetable"))

        entry = TimeTable(subject = sub, sem = sem, batch=batch,slot=slot,
                          faculty_name = name,faculty_id=faculty_id)
        #db.create_all()
        db.session.add(entry)
        try:
            db.session.commit()
        except:
            flash("Database is locked")
            db.session.rollback()
            #db.session.close()
        flash("Data added", "success")
        return redirect(url_for("timetable"))

    return render_template("Admin/add_lecture.html")

@app.route("/student-total-attendance", methods=["GET","POST"])
@student_login_required
def student_total_attendance():
    #count total days
    start_term = dt.date(2021, 4, 20)
    today = dt.date(2021,5,10)
    end_term = min(datetime.today().date(),today)
    total_days = np.busday_count(start_term, end_term)+1

    #get student id, student name & batch
    user_id = current_user.userid
    email = user.query.filter_by(userid=user_id).first().email
    student_id = Student.query.filter_by(email = email).first()

    if not student_id:
        flash("Can't open Attendance Page, First upload your pictures here!","danger")
        return redirect(url_for("add_photos"))

    student_id = student_id.id

    #get Stdent data
    student = Student.query.filter_by(id = student_id).first()
    name = student.name
    batch = student.sem + "-" + "G" #student.div
    user_data = {"name": name, "batch": batch,"start_term":start_term,"total":total_days}

    #getting all lectures are which are attended
    attended_lecs = Attendence.query.filter_by(student_id = student_id).all()

    #count total attendance of particular subject
    attended_lecs_ids = {}
    for each in attended_lecs:
        try:
            attended_lecs_ids[each.timetable_id] += 1
        except:
            attended_lecs_ids[each.timetable_id] = 1

    print(attended_lecs_ids)
    row = []

    #TimeTable rows
    lecs = TimeTable.query.all()

    for lec in lecs:
        temp = {"subject":lec.subject,"slot":lec.slot,"present":0}

        #note total attendance
        if lec.id in attended_lecs_ids:
            temp['present'] = attended_lecs_ids[lec.id]
        row.append(temp)

    print(user_data)
    print(row)

    '''
    user_data.keys= name,batch
    row.keys = slot,subject,time,status
    '''


    return render_template("total_attendance.html",row=row,user_data=user_data)

@app.route("/student-today-attendance", methods=["GET","POST"])
@student_login_required
def student_today_attendance():
    today_date = str(datetime.today().date())
    #get student id, student name & batch
    user_id = current_user.userid
    email = user.query.filter_by(userid=user_id).first().email
    student_id = Student.query.filter_by(email = email).first()
    if not student_id:
        flash("Can't open Attendance Page, First upload your pictures here!","danger")
        return redirect(url_for("add_photos"))
    student_id = student_id.id
    student = Student.query.filter_by(id = student_id).first()
    name = student.name
    batch = student.sem + "-" + "G" #student.div
    user_data = {"name": name, "batch": batch}

    #getting which lectures are attended
    attended_lecs = Attendence.query.filter_by(student_id = student_id,date=today_date).all()
    attended_lecs_ids = [each.timetable_id for each in attended_lecs]
    print(attended_lecs_ids)
    row = []

    #TimeTable rows
    lecs = TimeTable.query.all()

    for lec in lecs:
        temp = {"subject":lec.subject, "slot":lec.slot,"time":"-","status":"absent"}
        if lec.id in attended_lecs_ids:
            time = Attendence.query.filter_by(student_id=student_id,timetable_id=lec.id).first().time
            temp['time'] = time
            temp["status"] = "PRESENT"
        row.append(temp)

    print(user_data)
    print(row)

    '''
    user_data.keys= name,batch
    row.keys = slot,subject,time,status
    '''


    return render_template("attendance.html",row=row,user_data=user_data)

@app.route("/faculty-attendance", methods=["GET","POST"])
@faculty_login_required
def faculty_attendance():
    faculty_id = current_user.userid
    row = TimeTable.query.filter_by(faculty_id=faculty_id).first()
    if not row:
        flash("First Add you Lecture Here!","danger")
        return redirect(url_for("timetable"))
    #get subject of current faculty
    subject = row.subject
    #get time table id of that subject
    tt_id = row.id

    today_date = str(datetime.today().date())

    #students will be sorted based on today's date & current faculty's time table id
    present_students = Attendence.query.filter_by(date=today_date,timetable_id=tt_id).all()

    detail = {"subject":subject,"date":today_date}
    data = []
    for each in present_students:
        temp = {"time":each.time}
        s = Student.query.filter_by(id = each.student_id).first()
        t = TimeTable.query.filter_by(id = each.timetable_id).first()
        temp["name"] = s.name
        temp["enrollment"] = s.enrollment
        temp["subject"] = t.subject
        temp["batch"] = t.batch
        temp["slot"] = t.slot
        data.append(temp)

    return render_template("Admin/attendance.html",data = data,detail = detail)

@app.route("/faculty-total-attendance", methods=["GET","POST"])
@faculty_login_required
def faculty_total_attendance():
    # count total days
    start_term = dt.date(2021, 4, 20)
    today = dt.date(2021, 5, 10)
    end_term = min(datetime.today().date(), today)
    total_days = np.busday_count(start_term, end_term)+1
    faculty_id = current_user.userid

    row = TimeTable.query.filter_by(faculty_id=faculty_id).first()
    if not row:
        flash("First Add you Lecture Here!","danger")
        return redirect(url_for("timetable"))
    #get subject of current faculty
    subject = row.subject

    #get time table id of that subject
    tt_id = row.id
    lecture_detail = {"subject":subject,"slot":row.slot,"total":total_days,"start_term":start_term}
    student_rows = Student.query.all()

    data = []
    for student in student_rows:
        temp = {"name":student.name,"enrollment":student.enrollment,
                "batch":student.sem+"-G"}
        student_user_id = student.id
        #student_user_id = user.query.filter_by(email=student.email).first().userid
        present_count = len(Attendence.query.filter_by(timetable_id=tt_id,student_id=student_user_id).all())
        print(student_user_id,present_count)
        temp['present'] = present_count
        data.append(temp)

    return render_template("Admin/total_attendance.html",data = data,lecture_detail = lecture_detail)

@app.route("/user-register",methods=["GET", "POST"])
def userregister():
    if current_user.is_authenticated and current_user.type == "student":
        return redirect(url_for('home'))
    form = UserRegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.hashpw(form.password.data.encode('utf-8'),bcrypt.gensalt())
        hashed_confirmpassword = bcrypt.hashpw(form.confirmpassword.data.encode('utf-8'), bcrypt.gensalt())
        #hashed_confirmpassword = bcrypt.generate_password_hash(form.confirmpassword.data).decode('utf-8')
        entry = user(username = form.username.data, email = form.email.data, type="student", password = hashed_password, confirmpassword = hashed_confirmpassword )
        db.session.add(entry)
        db.session.commit()
        flash('Your account has been created! Welcome Home !', 'success')
        return redirect(url_for("home"))
    return render_template('user-registration.html',form = form, title='UserRegister')

@app.route("/faculty-register",methods=["GET", "POST"])
def facultyregister():
    print("faculty called!")
    if current_user.is_authenticated and current_user.type == "faculty":
        return redirect(url_for('facultyhome'))
    form = UserRegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.hashpw(form.password.data.encode('utf-8'),bcrypt.gensalt())
        hashed_confirmpassword = bcrypt.hashpw(form.confirmpassword.data.encode('utf-8'), bcrypt.gensalt())
        #hashed_confirmpassword = bcrypt.generate_password_hash(form.confirmpassword.data).decode('utf-8')
        entry = user(username = form.username.data, email = form.email.data, type="faculty", password = hashed_password, confirmpassword = hashed_confirmpassword )
        db.session.add(entry)
        db.session.commit()
        flash('Your account has been created! Welcome Home !', 'success')
        return redirect(url_for("facultyhome"))
    return render_template('Admin/faculty-registration.html',form = form, title='FacultyRegister')


@app.route("/add_photos", methods = ["GET","POST"])
@student_login_required
def add_photos():
    student_user_id = current_user.userid
    email = user.query.filter_by(userid = student_user_id).first().email
    student = Student.query.filter_by(email = email).first()
    #print(student_user_id,email,student)
    if student:
        flash("Can't open:You have already added photos","danger")
        return redirect(url_for("home"))
    if request.method == "POST":
        name = request.form["name"]
        enroll = request.form["enroll"]
        email = request.form["email"]
        branch = request.form["branch"]
        sem = request.form["sem"]

        print(sem)

        if name == "" or enroll == "" or branch == "Select the branch" or sem == "Select your semester":
            flash("Enter all Details", "danger")
            return render_template("profile.html")


        student = Student(enrollment=enroll, name=name, email=email,
                          sem=sem,
                          branch=branch,div="G")
        files_objects = []
        # folder name = student name
        folder_label = name
        valid_upload = 1
        # iterate throgh all images
        for number in range(1, len(request.files) + 1):
            file = request.files['img' + str(number)]
            if not file.filename:
                flash(f"Please Upload Image--{number}", "danger")
                valid_upload = 0
                break
            # elif not allowed_file(file.filename):
            #     flash(f"please upload image file in Image-{number}", "danger")
            #     valid_upload = 0
            elif file:
                path = os.path.join(app.config['UPLOAD_FOLDER'], folder_label, secure_filename(file.filename))
                files_objects.append([file, path])
                # file.save(path)

        # create a folder in train dataset & save 5 images there
        if valid_upload:
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_label)
            # make folder of student
            Path(folder_path).mkdir(parents=True, exist_ok=True)

            # save all images at given directory
            for file_path in files_objects:
                file_path[0].save(file_path[1])

            # save details in database
            # db.create_all()
            db.session.add(student)
            db.session.commit()

            flash("Data added successfully","success")
            return redirect(url_for("home"))

    return render_template("profile.html")





@app.route("/contact-us", methods = ["GET","POST"])
def contact_us():
    return render_template("contact-us.html")

@app.route("/faculty-contact-us", methods = ["GET","POST"])
def faculty_contact_us():
    return render_template("Admin/contact-us.html")

@app.route("/forget-password", methods = ["GET","POST"])
def forget_password():
    return render_template("forget-password.html")

@app.route("/login-user", methods=["GET","POST"])
def userlogin():
    if current_user.is_authenticated and current_user.type == "student":
        return redirect(url_for('home'))
    form = UserLoginForm()
    if form.validate_on_submit():
        entry = user.query.filter_by(email=form.email.data).first()
        if entry and entry.verify_password(form.password.data) and entry.type=="student":
            login_user(entry)
            return redirect(url_for('home'))
            flash('Successfully logged in !')
        else:
           flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login-user.html', form=form, title='UserLogin')

@app.route("/logout-user",methods=["GET","POST"])
@student_login_required
def logoutUser():
    logout_user()
    return redirect(url_for('home'))

@app.route("/logout-faculty",methods=["GET","POST"])
@faculty_login_required
def logoutFaculty():
    logout_user()
    return redirect(url_for('facultyhome'))

#############
#ADMIN Routes
#############

@app.route("/login-faculty", methods = ["GET","POST"])
def login_faculty():
    if current_user.is_authenticated and current_user.type == "faculty":
        return redirect(url_for('facultyhome'))
    form = UserLoginForm()
    if form.validate_on_submit():
        entry = user.query.filter_by(email=form.email.data).first()
        if entry and entry.verify_password(form.password.data) and entry.type == "faculty":
            login_user(entry)
            return redirect(url_for('facultyhome'))
            flash('Successfully logged in !')
        else:
           flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template("Admin/login-faculty.html",form=form, title='UserLogin')



@app.route("/login-admin", methods = ["GET","POST"])
def login_admin():
    return render_template("login-admin.html")

@app.route("/update-model", methods = ["GET","POST"])
@faculty_login_required
def update_model():
    print(os.getcwd())
    labels = modules.add_new_persons()
    #LiveFaceRecognition.camera()
    return render_template("Admin/update model.html",labels=labels)

@app.route("/camera", methods = ["GET","POST"])
@faculty_login_required
def on_camera():
    print(os.getcwd())
    #modules.add_new_persons()
    LiveFaceRecognition.camera()
    return render_template("Admin/index.html")
