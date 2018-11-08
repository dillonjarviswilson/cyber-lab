from app import app, db, models, setup
from flask import render_template, url_for, redirect, flash, request
from datetime import datetime
from app.models import Session, Activity
from app.forms import NewActivityForm
from sqlalchemy import desc, tuple_
import logging, logging.config, uuid
import atexit
from flask import jsonify
import subprocess

logfile    = logging.getLogger('file')
logconsole = logging.getLogger('console')

logfile.debug("Debug FILE")


def get_full_url(port):
    return str("http://ssrc-cluster.wireless.leeds.ac.uk:" + str(port))

def exit_handler():
    print("\n\nShutting down...")

    allSessions = Session.query.order_by(Session.user_number).all()

    for s in allSessions:
        print("Call to close: " + str(s.user_number))
        db.session.delete(s)
        db.session.commit()
	subprocess.call(['./stop.sh', str(s.user_number)])



atexit.register(exit_handler)



@app.route('/connect', methods=['GET'])
def main_session():

    logfile.debug("- New Connection -")

    session_id = request.args.get('s')
    container = request.args.get('c')

    if session_id == None:
        return render_template('not_found.html',
                                title='Session not found',
                                session_id=session_id)

    if container == None:
        return render_template('not_found.html',
                                title='Invalid Continer ref: use 1, 2 or 3',
                                session_id=session_id)

    logfile.debug("attempting to connect to: " + str(session_id))

    session_to_show = Session.query.filter_by(unique_identifier=session_id).first()

    if session_to_show != None:
        c = int(container)
        ref = None
        if c == 1: ref = session_to_show.ap_address
        elif c==2: ref = session_to_show.client_address
        elif c==3: ref = session_to_show.pos_address
        else:
            return render_template('not_found.html',
                                title='Invalid Continer ref: use 1, 2 or 3',
                                session_id=session_id)

        url_to_show = get_full_url(ref)

        return render_template('connection.html',
                            title='AP Terminal',
                            url=url_to_show,
                            url_client=get_full_url(session_to_show.client_address),
                            url_ap=get_full_url(session_to_show.ap_address),
                            url_pos=get_full_url(session_to_show.pos_address))
    else:
        #no session found
        return render_template('not_found.html',
                                title='Session not found',
                                session_id=session_id)
    
    


@app.route('/new', methods=['GET'])
def new():
    logfile.debug("making new session")
    
    dateNow = datetime.now()
    session_id = uuid.uuid4()

    top_session = db.session.query(db.func.max(Session.user_number)).scalar()

    if top_session == None:
        new = 0
    else:
        new = int(top_session) + 1

    print("Call to run session: " + str(new))
    
    a = (new * 3) + 4300
    b = (new * 3) + 4301
    c = (new * 3) + 4302


    new_session = models.Session(unique_identifier=str(session_id),
                                user_number=str(new),
                                ap_address=str(a),
                                client_address=str(b),
                                pos_address=str(c),
                                time_created=dateNow)

    #add and commit the db changes
    db.session.add(new_session)
    db.session.commit()


    subprocess.call(['./start.sh', str(new_session.user_number)])

    logfile.debug("Added session: " + str(new_session.id))
 
    query = str("/connect?" + "s=" + new_session.unique_identifier + "&c=1")

    return redirect(query)



@app.route('/', methods=['GET'])
def home():

    activities = Activity.query.filter_by(running=True).all()
    for a in activities:
        a.content = ""
        a.container = ""

    if len(activities) > 0:
        return render_template('root.html',
                                activites=activities)
    else:
        return render_template('404.html',
                                message="There are no available activites to run right now. Ask your teacher to add some.")



@app.route('/staff', methods=['GET'])
def staff():

    activities = Activity.query.all()

    for a in activities:
        print(a)
        a.content = ""
        a.container = ""

    return render_template('staff.html',
                            activities=activities)



@app.route('/staff/create', methods=['GET', 'POST'])
def staff_create_new():

    form = NewActivityForm()
    if form.validate_on_submit():
        flash('New activity created {}'.format(
            form.title.data))

        dateNow = datetime.now()

        new_activity = models.Activity(
                                running = False,
                                title = form.title.data,
                                category = form.category.data,
                                has_content = False,
                                has_containers = False,
                                time_created = dateNow,
                                content = "",
                                config = "",
                                description = form.description.data,
                                enabled = False,
                                is_ready = False,
                                number_of_students = 0,
                                number_of_containers = 0)

        #add and commit the db changes
        db.session.add(new_activity)
        db.session.commit()

        print("Added activity")

        return redirect('/staff')

    return render_template('create_new.html', title='Create New', form=form)



@app.route('/staff/activity/<int:activity_id>', methods=['GET'])
def staff_edit_activity(activity_id):

    activity = Activity.query.get(activity_id)


    if activity != None:

        if activity.content != "":
            activity_content = activity.content
        else:
            activity_content = False

        return render_template('control_activity.html', 
                                title = activity.title,
                                activity_id = activity.id,
                                activity_content = activity_content)

    else:
        return render_template('404.html', 
                            message="Could not find the activity.")

  



@app.route('/staff/action', methods = ['POST'])
def staff_action():
    id_number = request.form['activity_id']
    action = request.form['activity_action']

    activity = Activity.query.get(id_number)
    
    if activity != None:
        alert_icon = ""
        alert_color = ""
        alert_message = ""

        if action == "delete":
            db.session.delete(activity)
            db.session.commit()

            #not a valid start/stop action
            alert_icon = "fa fa-exclamation-circle"
            alert_color = "red"
            alert_message = "The activity has been deleted."
        


        elif activity.has_containers != True:
            #inform the user
            alert_icon = "fa fa-exclamation-circle"
            alert_color = "orange"
            alert_message = "The activity has no container model. You need to define one before running."
        elif activity.has_content != True:
            #inform the user
            alert_icon = "fa fa-exclamation-circle"
            alert_color = "orange"
            alert_message = "The activity has no lesson content. You need to create if before running."
        elif activity.enabled == False:
            #inform the user
            alert_icon = "fa fa-exclamation-circle"
            alert_color = "red"
            alert_message = "The activity has been disabled, enable it first."
        else:
            if action == "start":
                if activity.running == True:
                    #inform the user
                    alert_icon = "fa fa-exclamation-circle"
                    alert_color = "red"
                    alert_message = "The activity is already running."
                else:
                    alert_icon = "fa fa-check"
                    alert_color = "green"
                    alert_message = "The activity is running and visible to students."
            elif action == "stop":
                if activity.running == False:
                    #inform the user
                    alert_icon = "fa fa-exclamation-circle"
                    alert_color = "red"
                    alert_message = "The activity is not running."
                else:
                    alert_icon = "fa fa-check"
                    alert_color = "green"
                    alert_message = "The activity has been stopped and is not visible to students."
            else:
                #not a valid start/stop action
                alert_icon = "fa fa-exclamation-circle"
                alert_color = "red"
                alert_message = "Not a valid operation on activity"
        
        return jsonify(icon=alert_icon,
                        color=alert_color,
                        content=alert_message)

    else:
        return render_template('404.html', 
                            message="Could not find activity.")



@app.route('/staff/create_content/<int:id_number>', methods = ['GET'])
def staff_create_content(id_number):
    activity = Activity.query.get(id_number)
    if activity != None:
        return render_template('create_content.html', 
                                title='Create Content',
                                activity_id = activity.id)
    else:
        return render_template('404.html', 
                            message="Could not find activity.")




@app.route('/staff/add_content', methods = ['POST'])
def staff_submit_content():
    id_number = request.form['activity_id']
    content = request.form['content']

    activity = Activity.query.get(id_number)

    alert_icon = ""
    alert_color = ""
    alert_message = ""

    if activity != None:     
        activity.content = content

        db.session.commit()

        alert_icon = "fa fa-check"
        alert_color = "green"
        alert_message = "The activity content has been saved."

        return jsonify(icon=alert_icon,
                        color=alert_color,
                        content=alert_message)

    else:
        return render_template('404.html', 
                            message="Could not find activity.")