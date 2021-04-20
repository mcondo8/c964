from flask import Flask, jsonify, request, render_template, url_for, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api
from scrip_parser import PrescriptionParser
from werkzeug.utils import secure_filename
import scrip_parser
import label_unwrap
import hashlib
import uuid
from datetime import datetime, date, timedelta, timezone
# from webui import WebUI

import os

TEMPLATES_DIR = 'templates'
TEMP_IMG_DIR = 'uploads'
VALID_IMG_TYPES = {'jpg', 'jpeg'}

app = Flask(__name__, template_folder=TEMPLATES_DIR)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scripts.db'
app.config['UPLOAD_FOLDER'] = TEMP_IMG_DIR
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "ccpor_secret_key_89017d"
app.config['SESSION_TYPE'] = 'filesystem'

db = SQLAlchemy(app)

""" DATA CLASSES FOR SQLALCHEMY """


class User(db.Model):
    username = db.Column(db.String(50), nullable=False, primary_key=True)
    passhash = db.Column(db.String(500), nullable=False)
    first_name = db.Column(db.String(500), nullable=False)
    last_name = db.Column(db.String(500), nullable=False)
    email = db.Column(db.String(500), nullable=False)
    pref_morning = db.Column(db.String, nullable=False)
    pref_breakfast = db.Column(db.String, nullable=False)
    pref_lunch = db.Column(db.String, nullable=False)
    pref_dinner = db.Column(db.String, nullable=False)
    pref_night = db.Column(db.String, nullable=False)
    is_admin = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        "{fname} {lname}".format(fname=self.first_name, lname=self.last_name)


class user_activity_log(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    action = db.Column(db.String(10), nullable=False)
    src = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.String(30), nullable=False, default='CURRENT_TIMESTAMP')
    uid = db.Column(db.String(50), nullable=False)
    p_guid = db.Column(db.String(50), nullable=False)

    def __init__(self, action, src, uid):
        self.action = action
        self.src = src
        self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        self.uid = uid


class PrescriptionImage(db.Model):
    p_guid = db.Column(db.String, nullable=False, primary_key=True)
    point_ax = db.Column(db.Float, nullable=False)
    point_ay = db.Column(db.Float, nullable=False)
    point_bx = db.Column(db.Float, nullable=False)
    point_by = db.Column(db.Float, nullable=False)
    point_cx = db.Column(db.Float, nullable=False)
    point_cy = db.Column(db.Float, nullable=False)
    point_dx = db.Column(db.Float, nullable=False)
    point_dy = db.Column(db.Float, nullable=False)
    point_ex = db.Column(db.Float, nullable=False)
    point_ey = db.Column(db.Float, nullable=False)
    point_fx = db.Column(db.Float, nullable=False)
    point_fy = db.Column(db.Float, nullable=False)

    def __init__(self, p_guid,
                 point_ax,
                 point_ay,
                 point_bx,
                 point_by,
                 point_cx,
                 point_cy,
                 point_dx,
                 point_dy,
                 point_ex,
                 point_ey,
                 point_fx,
                 point_fy):
        self.p_guid = p_guid
        self.point_ax = point_ax
        self.point_ay = point_ay
        self.point_bx = point_bx
        self.point_by = point_by
        self.point_cx = point_cx
        self.point_cy = point_cy
        self.point_dx = point_dx
        self.point_dy = point_dy
        self.point_ex = point_ex
        self.point_ey = point_ey
        self.point_fx = point_fx
        self.point_fy = point_fy


class Prescription(db.Model):
    p_guid = db.Column(db.String(45), nullable=False, primary_key=True)
    drug_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    end_date = db.Column(db.String(8), nullable=False)
    start_date = db.Column(db.String(8), nullable=False)
    status = db.Column(db.Integer, nullable=False)
    is_deleted = db.Column(
        db.Integer)  # Really a bool, but a tiny integer is used to hold 1/0 for more database compatibility
    timezone = db.Column(db.String)

    def __init__(self,
                 presc_guid,
                 drug_name,
                 username,
                 end_date,
                 start_date,
                 status):
        self.p_guid = presc_guid
        self.drug_name = drug_name
        self.username = username
        self.start_date = start_date
        self.end_date = end_date
        self.status = status


class PrescriptionSchedule(db.Model):
    prescription_guid = db.Column(db.String(45), nullable=False, primary_key=True)
    schedule_sqn = db.Column(db.Integer, nullable=False, primary_key=True)
    value = db.Column(db.String(50), nullable=False)

    def __init__(self, presc_guid, sqn, value):
        self.prescription_guid = presc_guid
        self.schedule_sqn = sqn
        self.value = value


""" END DATA CLASSES """

""" API ROUTES AND FUNCTIONS """


@app.route("/")
def home():
    """Serve the login page"""
    return render_template("login_page.html", frmact="/web/login")


@app.route("/web/login", methods=['POST'])
def web_login():
    if not ('user' in request.form and
            'password' in request.form):
        return render_template("login_page.html", error="Username and Password are required.")
    usr = request.form['user']
    passwd = request.form['password'].encode('utf-8')

    if usr == "" or passwd == "":
        return render_template("login_page.html", error="Username and Password are required.")

    hashed_passwd = hashlib.sha1(passwd).hexdigest()

    if not validate_user(usr, hashed_passwd):
        return render_template("login_page.html", error="Username or Password Incorrect", frmact="")

    is_admin = validate_admin(usr, hashed_passwd)

    session['username'] = usr
    session['passhash'] = hashed_passwd
    session['is_admin'] = is_admin

    return redirect("/web/dashboard")


@app.route("/web/dashboard/", methods=['POST', 'GET'])
def dashboard():
    if (session.get('username') is None or
            session.get('passhash') is None or
            session.get('is_admin') is None):
        return redirect("web/login", 307)
    usr = session['username']
    phash = session['passhash']

    if session['is_admin']:
        if not validate_admin(usr, phash):
            return redirect("/web/login", 307)
        return render_admin_template(usr)  # render_template("admin_dashboard.html", username=usr)
    else:
        if not validate_user(usr, phash):
            return redirect("./web/login", 307)
        return render_template("user_dashboard.html", username=usr)


@app.route('/api/<string:username>/parse_script', methods=['POST'])
def parse_script(username):
    if request.method == 'POST':
        if not (len(request.files) > 0 and
                'p1' in request.form and
                'p2' in request.form and
                'p3' in request.form and
                'p4' in request.form and
                'p5' in request.form and
                'p0' in request.form and
                'uname' in request.form and
                'phash' in request.form):
            return 'Missing required values', 400
        file = request.files['file']
        if file.filename == '':
            return "No File Uploaded", 400
        if not is_allowed_type(file.filename):
            return "Invalid Filetype", 400

        # clean up file in case it's a dangerous type
        # sec_file = secure_filename(file.filename)
        new_uuid = uuid.uuid4()
        str_uuid = str(new_uuid).replace("-", "")
        sec_file = app.config['UPLOAD_FOLDER'] + "/" + str_uuid + ".jpg"
        unwrapped_file = app.config['UPLOAD_FOLDER'] + "/" + str_uuid + "_unwrapped.jpg"

        # stash the file - we can now begin processing
        file.save(sec_file)

        p0 = request.form['p0'].split(",")
        p0x = p0[0]
        p0y = p0[1]

        p1 = request.form['p1'].split(",")
        p1x = p1[0]
        p1y = p1[1]

        p2 = request.form['p2'].split(",")
        p2x = p2[0]
        p2y = p2[1]

        p3 = request.form['p3'].split(",")
        p3x = p3[0]
        p3y = p3[1]

        p4 = request.form['p4'].split(",")
        p4x = p4[0]
        p4y = p4[1]

        p5 = request.form['p5'].split(",")
        p5x = p5[0]
        p5y = p5[1]

        insert_script_image(str_uuid,
                            float(p0x), float(p0y),
                            float(p1x), float(p1y),
                            float(p2x), float(p2y),
                            float(p3x), float(p3y),
                            float(p4x), float(p4y),
                            float(p5x), float(p5y))

        shape = {"tag": "label", "shape": [{"x": float(p0x), "y": float(p0y)},
                                           {"x": float(p1x), "y": float(p1y)},
                                           {"x": float(p2x), "y": float(p2y)},
                                           {"x": float(p3x), "y": float(p3y)},
                                           {"x": float(p4x), "y": float(p4y)},
                                           {"x": float(p5x), "y": float(p5y)}]}

        PrescriptionParser.flatten_image(sec_file, shape)
        script_text = PrescriptionParser.process_image(unwrapped_file)
        script_res = PrescriptionParser.string_to_prescription(script_text)
        script_drug = PrescriptionParser.parse_drug_name(script_text)
        start_date = date.today()
        end_date = date.today() + timedelta(days=7)
        str_start_date = start_date.strftime("%Y%m%d")
        str_end_date = end_date.strftime("%Y%m%d")

        insert_prescription(script_drug, username, str_end_date, str_start_date, str_uuid, script_res)

        res = jsonify(
            drug=script_drug,
            admin_times=script_res,
            script_id=str_uuid,
            start_date=str_start_date,
            end_date=str_end_date
        )
        return res, 200

        # Write the file to our database
        # Re-assemble points into an array, run the parser


@app.route('/api/create_user', methods=['POST'])
def create_user():
    if ('user' in request.args and
            'passhash' in request.args and
            'fullname' in request.args and
            'email' in request.args):
        # Verify user doesn't already exist
        #   If exists, return 409 conflict
        user = request.args['user']
        passhash = request.args['passhash']
        fullname = request.args['fullname']
        email = request.args['email']

        if not user_exists(user):
            # Enter user into the database
            #   Success: Return 201
            #   Failure: Return 406
            if create_user(user, passhash, fullname, email):
                return "User Created", 201
            else:
                # todo
                # create an error log record here as well
                return "Failed to create user. Please contact support for assistance.", 406
        else:
            return "User Already Exists", 406
    else:
        # Return 406 - not acceptable
        return "Missing Required Values", 406


@app.route('/api/login', methods=['POST'])
def login():
    """

    :param uname:
    :param phash:
    :return:
    """
    try:
        if not ('uname' in request.form and
                'phash' in request.form):
            return 'Invalid Request', 400

        uname = request.form['uname']
        phash = request.form['phash']

        if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            src_ip = request.environ['REMOTE_ADDR']
        else:
            src_ip = request.environ['HTTP_X_FORWARDED_FOR']  # if behind a proxy

        if validate_user(uname, phash):
            insert_user_log("L200", src_ip, uname)
            usr = get_user(uname)
            return usr, 200
        else:
            insert_user_log("L401", src_ip, uname)
            return 'Unknown User', 401
    except RuntimeError:
        insert_user_log("L403", src_ip, uname)
        return 'Login Failure', 403


@app.route('/api/<string:user>/get_scripts', methods=['POST'])
def get_scripts(user):
    """
    Get user's list of previous prescriptions
    :param user:
    :return:
    """
    # try:
    if not ('passhash' in request.form):
        return "INVALID USER", 400
    passhash = request.form['passhash']
    if not (validate_user(user, passhash)):
        return "UNAUTHORIZED USER", 400
    return get_user_scripts(user), 200
    # except RuntimeError:
    #    return []  # TODO Add Logging here
    return []


@app.route('/api/<string:user>/<string:script_guid>/update_script', methods=['POST'])
def update_script(user, script_guid):
    """
    Write in the final list of corrected times selected by the user
    For later reference and dataset training
    :param user:
    :param script_id:
    :return:
    """
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        src_ip = request.environ['REMOTE_ADDR']
    else:
        src_ip = request.environ['HTTP_X_FORWARDED_FOR']  # if behind a proxy

    if not ('passhash' in request.form and
            'p_guid' in request.form and
            'drug' in request.form and
            'start' in request.form and
            'end' in request.form and
            'admin_times' in request.form and
            'status' in request.form):
        # Error - kick it back
        insert_user_log("U400", src_ip, user)
        return "Missing Required Values", 400

    p_guid = request.form['p_guid']
    drug_name = request.form['drug']
    p_guid = request.form['p_guid']
    start = request.form['start']
    end = request.form['end']
    passhash = request.form['passhash']

    if not validate_user(user, passhash):
        insert_user_script_log("U401", src_ip, user, p_guid)
        return "UNAUTHORIZED USER", 401

    # if isinstance(request.form['admin_times'], str):
    admin_times = request.form['admin_times'].split(",")
    # else:
    #     admin_times = request.form['admin_times']
    drg_status = request.form['status']

    if update_prescription(drug_name, user, end, start, p_guid, drg_status, admin_times):
        insert_user_log("U200", src_ip, user)
        return "Script Updated", 200

    return "Script Update Failed", 400


@app.route('/api/<string:user>/<string:script_guid>/delete_script', methods=['POST'])
def delete_script(user, script_guid):
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        src_ip = request.environ['REMOTE_ADDR']
    else:
        src_ip = request.environ['HTTP_X_FORWARDED_FOR']  # if behind a proxy

    if not ('passhash' in request.form):
        insert_user_log("D400", src_ip, user)
        return "Missing Required Values", 400

    if not validate_user(user, request.form['passhash']):
        insert_user_log("D401", src_ip, user)
        return "UNAUTHORIZED USER", 401

    if delete_prescription(script_guid, user):
        insert_user_log("D200", src_ip, user)
        return "SCRIPT DELETED", 200
    else:
        insert_user_log("D400", src_ip, user)
        return "DELETE FAILED", 400


""" END API FUNCTIONS """

""" HELPER FUNCTIONS """


def is_allowed_type(filename):
    if '.' in filename and filename.rsplit('.', 1)[1] in VALID_IMG_TYPES:
        return True
    return False


def get_user_scripts(user):
    # user = db.session.query(User, Role.index).join(Role).filter(User.email==form.email.data).first()
    query_result = db.session.query(Prescription, PrescriptionSchedule) \
        .join(PrescriptionSchedule, Prescription.p_guid == PrescriptionSchedule.prescription_guid) \
        .filter(Prescription.p_guid == PrescriptionSchedule.prescription_guid,
                Prescription.is_deleted == 0, Prescription.username == user) \
        .order_by(Prescription.start_date, Prescription.p_guid, PrescriptionSchedule.schedule_sqn)

    rtn = {}
    i = 0
    for presc, schd in query_result:
        rtn[str(i)] = {"p_guid": presc.p_guid, "drug": presc.drug_name,
                       "user": presc.username, "start": presc.start_date,
                       "end": presc.end_date, "sqn": schd.schedule_sqn,
                       "schedule_value": schd.value, "status": presc.status}
        i += 1
    return rtn


def user_exists(uname):
    """
    Check the existence of a username in the database
    :param username:
    :return:
    """
    if User.query.filter_by(username=uname).count() > 0:
        return True
    else:
        return False


def create_user(uname, phash, fname, lname, email_addr):
    """
    Create a user in the database
    Return True if the user is created, false otherwise
    In event user fails to create, log error
    :param email_addr:
    :param username:
    :param passhash:
    :param fullname:
    :param email:
    :return:
    """
    if user_exists(uname):
        return False
    try:
        nusr = User(username=uname, passhash=phash, first_name=fname, last_name=lname, email=email_addr)
        db.session.add(nusr)
        db.session.commit()
        return True
    except RuntimeError:
        return False  # TODO Add Logging here
    return False


def validate_user(uname, phash):
    """
    Check if username/password pair exists in the database
    Return true if found, false otherwise
    :param user:
    :param passhash:
    :return:
    """
    if User.query.filter_by(username=uname, passhash=phash).count() > 0:
        return True
    else:
        return False
    return False


def validate_admin(uname, phash):
    """
    Check if username/password pair exists in the database wiht admin flag set
    Return true if found, false otherwise
    :param user:
    :param passhash:
    :return:
    """
    if User.query.filter_by(username=uname, passhash=phash, is_admin=1).count() > 0:
        return True
    else:
        return False
    return False


def get_user(uname):
    """
    Get user details as a python dictionary from the database
    :param user:
    :return: {} of user details
    """
    query_result = User.query.filter_by(username=uname)
    rtn = {}
    if query_result.count() == 1:
        usr = query_result.first()
        rtn["first_name"] = usr.first_name
        rtn["last_name"] = usr.last_name
        rtn["email"] = usr.email
        rtn["pref_breakfast"] = usr.pref_breakfast
        rtn["pref_lunch"] = usr.pref_lunch
        rtn["pref_dinner"] = usr.pref_dinner
        rtn["pref_morning"] = usr.pref_morning
        rtn["pref_night"] = usr.pref_night

        return rtn
    else:
        return


def insert_prescription(drug_name,
                        username,
                        end_date,
                        start_date,
                        guid,
                        admin_times):
    # Insert a new prescription into the database
    try:
        presc = Prescription(guid, drug_name, username, end_date, start_date, 0)
        presc.is_deleted = 0
        db.session.add(presc)

        i = 0
        for tm in admin_times:
            a_time = PrescriptionSchedule(guid, i, tm)
            db.session.add(a_time)
            i += 1

        db.session.commit()
        insert_user_script_log("P200", drug_name, username, guid)
        return True

    except RuntimeError:
        insert_user_script_log("P400", drug_name, username, guid)
        return False  # TODO Add Logging here
    return False


def delete_prescription(guid, username):
    try:
        db.session.query(Prescription).filter(Prescription.p_guid == guid).update({Prescription.is_deleted: 1},
                                                                                  synchronize_session=False)
        insert_user_script_log("D200", "PRESCRIPTION DELETED", username, guid)
        db.session.commit()
        return True
    except RuntimeError:
        insert_user_log("D401", guid, username)
        return False  # TODO Add Logging here
    return False


def update_prescription(drug_name,
                        username,
                        end_date,
                        start_date,
                        guid,
                        status,
                        admin_times):
    # Insert a new prescription into the database
    try:
        db.session.query(Prescription).filter(Prescription.p_guid == guid).update({
            Prescription.drug_name: drug_name,
            Prescription.end_date: end_date,
            Prescription.start_date: start_date,
            Prescription.status: status}, synchronize_session=False)

        for a_time in db.session.query(PrescriptionSchedule).filter(PrescriptionSchedule.prescription_guid == guid):
            db.session.delete(a_time)

        i = 0
        for tm in admin_times:
            a_time = PrescriptionSchedule(guid, i, tm)
            db.session.add(a_time)
            i += 1

        db.session.commit()
        insert_user_script_log("P201", drug_name + "UPDATED", username, guid)
        return True
    except RuntimeError:
        insert_user_script_log("P401", drug_name + "UPDATED", username, guid)
        return False  # TODO Add Logging here
    return False


def insert_user_log(action, msg, uid):
    try:
        log = user_activity_log(action, msg, uid)
        db.session.add(log)
        db.session.commit()
        return True
    except RuntimeError:
        return False  # TODO Add Logging here
    return False


def insert_user_script_log(action, msg, uid, p_guid):
    try:
        log = user_activity_log(action, msg, uid)
        log.p_guid = p_guid
        db.session.add(log)
        db.session.commit()
        return True
    except RuntimeError:
        return False  # TODO Add Logging here
    return False


def insert_script_image(p_guid,
                        point_ax,
                        point_ay,
                        point_bx,
                        point_by,
                        point_cx,
                        point_cy,
                        point_dx,
                        point_dy,
                        point_ex,
                        point_ey,
                        point_fx,
                        point_fy):
    try:
        p_img = PrescriptionImage(p_guid, point_ax, point_ay, point_bx,
                                  point_by, point_cx, point_cy, point_dx,
                                  point_dy, point_ex, point_ey, point_fx,
                                  point_fy)
        db.session.add(p_img)
        db.session.commit()
        return True
    except RuntimeError:
        return False
    return False


""" END HELPER FUNCTIONS """

""" WEB TEMPLATE FUNCTIONS """


def render_admin_template(usr):
    labels = []
    values_success = []
    values_fail = []

    labels_avg = []
    values_avg = []

    labels_drg = []
    values_drg = []

    # This is a raw SQL query, since it cannot be expressed well in SQLAlchemy's native
    # access model

    sql_user_access_stmts = """
    SELECT tsrng.time_range as `time_range`, action, count(action) as `a_count` 
    FROM
        (SELECT action, 
            CASE
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-1 Hour') and datetime('now') then 1
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-2 Hour') and datetime('now', '-1 hours') then 2
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-3 Hour') and datetime('now', '-2 hours') then 3
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-4 Hour') and datetime('now', '-3 hours') then 4
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-5 Hour') and datetime('now', '-4 hours') then 5
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-6 Hour') and datetime('now', '-5 hours') then 6
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-7 Hour') and datetime('now', '-6 hours') then 7
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-8 Hour') and datetime('now', '-7 hours') then 8
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-9 Hour') and datetime('now', '-8 hours') then 9
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-10 Hour') and datetime('now', '-9 hours') then 10
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-11 Hour') and datetime('now', '-10 hours') then 11
            WHEN datetime(user_activity_log.timestamp) between datetime('now', '-12 Hour') and datetime('now', '-11 hours') then 12
            end as time_range
        from user_activity_log
        WHERE action IN  ('L200', 'L401')
        AND datetime(user_activity_log.timestamp) > datetime('now', '-12 hours')) tsrng
    GROUP BY `time_range`, `action`
    ORDER BY `time_range`, `action`;
    """

    rs = db.engine.execute(sql_user_access_stmts)

    for rec in rs:
        if not labels.__contains__(str(rec['time_range']) + " Hrs. Ago"):
            labels.append(str(rec['time_range']) + " Hrs. Ago")
        if rec['action'] == 'L200':
            values_success.append(rec['a_count'])
        else:
            values_fail.append(rec['a_count'])

    bar_labels = labels
    bar_success_values = values_success
    bar_fail_values = values_fail

    sql_get_script_averages = """SELECT tbl_avgs.drug as `drug`, avg(tbl_avgs.sch_count) as `average_schedule` FROM
        (SELECT username, prescription.drug_name as `drug`, count(prescription_schedule.schedule_sqn) as sch_count
        FROM prescription INNER JOIN prescription_schedule ON prescription.p_guid = prescription_schedule.prescription_guid
        GROUP BY prescription.username, prescription.p_guid, prescription.drug_name) tbl_avgs
        WHERE tbl_avgs.drug IS NOT NULL and tbl_avgs.drug <> ''
        GROUP BY tbl_avgs.drug
        ORDER BY drug"""

    rs = db.engine.execute(sql_get_script_averages)
    for rec in rs:
        labels_avg.append(rec['drug'])
        values_avg.append(rec['average_schedule'])

    sql_get_drug_counts = """select `drug_name` as drug_name, count(*) as `dn_count` 
    FROM prescription WHERE drug_name IS NOT NULL
    AND drug_name <> ''
    GROUP BY drug_name
    ORDER BY dn_count DESC;"""
    rs = db.engine.execute(sql_get_drug_counts)

    for rec in rs:
        labels_drg.append(rec['drug_name'])
        values_drg.append(rec['dn_count'])

    return render_template("admin_dashboard.html",
                           username=usr, labels=bar_labels,
                           success_values=bar_success_values,
                           fail_values=bar_fail_values,
                           chart_1_title='User Login Success and Failure',
                           max=5,
                           avg_script_labels=labels_avg,
                           avg_script_values=values_avg,
                           chart_2_title='Average Drug Admins Per Day',
                           chart_3_title='Current Prescriptions Per Drug',
                           drg_count_labels=labels_drg,
                           drg_count_data=values_drg)


""" END WEB TEMPLATE FUNCTIONS """

if __name__ == "__main__":
    app.run(debug=True)

# TODO
# Functions to create
# Create User - Done
#   Check if user is valid name
#   Assume password pre-hashed, using SHA1
#   Check if username already exists
# Validate User - Done
#   Take in hashed password + username
#   Check against DB, return true/false
# Get User's Script List
#   Validate user, get list of previously uploaded script
# Upload corrected script
#   After file uploaded, script timing list returned - return the final accepted prescription
# Uploads Per Timeframe dashboard
