from app import app, db, models, setup
from flask import render_template, url_for, redirect, flash, request
from datetime import datetime
from app.models import Session
from sqlalchemy import desc, tuple_
import logging, logging.config, uuid
import atexit
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
	return render_template('root.html',
                                title='Weclome')

