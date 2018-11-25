from app import app, db, models, setup
from flask import render_template, url_for, redirect, flash, request
from datetime import datetime
from app.models import Session, Activity, Container, PortTable
from app.forms import NewActivityForm, NewContainerForm
from sqlalchemy import desc, tuple_
import docker
import logging, logging.config, uuid
import atexit
from flask import jsonify
import subprocess


logfile    = logging.getLogger('file')
logconsole = logging.getLogger('console')

logfile.debug("Debug FILE")

DockerClient = docker.APIClient(base_url='tcp://127.0.0.1:1234')
sessionTracker = {}


def get_full_url(port):
    return str("http://ssrc-cluster.wireless.leeds.ac.uk:" + str(port))

def exit_handler():
    print("\n\nShutting down...")

    if Session:
        allSessions = Session.query.all()

        if allSessions != None:
            for s in allSessions:
                print("Call to close: " + str(s.unique_identifier))

                container_instance_list = sessionTracker[s.unique_identifier]
                
                for c in container_instance_list:
                    c.remove()
                    print("Removed")

                db.session.delete(s)
                db.session.commit()


atexit.register(exit_handler)



@app.route('/connect', methods=['GET'])
def main_session():

    logfile.debug("- New Connection -")

    session_id = request.args.get('s')
    container = request.args.get('c')

    if session_id == None:
        return render_template('not_found.html',
                                title='Specify a session',
                                session_id=session_id)

    if container == None:
        return render_template('not_found.html',
                                title='specify container ref',
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
                                title='Invalid Continer ref',
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

    #get activty ID
    aid = request.args.get('aid')

    if aid == None:
        return render_template('404.html', message="Specify activity ID")

    activity = Activity.query.get(aid)

    if activity == None:
        return render_template('404.html', message="Invalid activity ID")

    if activity.running == False:
        return render_template('404.html', message="Activity not available")

    #activity must be avail to students so go ahead and create session

    #ports_list, desc_list, container_id, container_ref = get_ports_list(activity.id)
    container_list, num_ports = get_list(activity.id)
    
    print("Number of ports: {}".format(num_ports))
    print(container_list)
    
    for cont in container_list:
        print(cont.port_list_internal)
        for int_port in cont.port_list_internal:
            ext_port = get_avail_port()
            print(cont.container.name)
            if ext_port == False: return render_template('404.html', message="Can not run, max capacity reached")
            
            new_entry = models.PortTable(
                            session_id=str(session_id),
                            friendly_name=str(cont.desc),
                            external_port=ext_port,
                            internal_port=int_port,
                            container_id=cont.container.id)

            cont.port_list_external.append(ext_port)

            db.session.add(new_entry)
            db.session.commit()

            print("Port {} routed to {} on container".format(ext_port, int_port))

    container_instance_list = []
    for cont in container_list:
        print("Call to run container")
        portDict = {}
        
        print(portDict)
        print(cont.port_list_internal)

        for x in range(0, len(cont.port_list_internal)):
            portDict[cont.port_list_external[x]] = cont.port_list_internal[x]
        
        print(portDict)

        docker_container_instance = DockerClient.create_container(
                cont.container.image, ports=cont.port_list_internal,
                host_config=docker.utils.create_host_config(port_bindings=str(portDict))
        )

        container_instance_list.append(docker_container_instance)
                
        print("Container Name: {} \tInternal Port: {}\t External Port: {}".format())
    

    new_session = models.Session(unique_identifier=str(session_id),
                                user_number=str(new),
                                time_created=dateNow,
                                activity_id=activity.id,
                                number_of_ports=num_ports)

    #add and commit the db changes
    db.session.add(new_session)
    db.session.commit()

    sessionTracker[session_id] = container_instance_list

    #subprocess.call(['./start.sh', str(new_session.user_number)])

    logfile.debug("Added session: " + str(new_session.id))
 
    query = str("/connect?" + "s=" + new_session.unique_identifier + "&c=1")

    return redirect(query)



@app.route('/', methods=['GET'])
def home():

    activities = Activity.query.filter_by(running=True).all()

    if len(activities) > 0:
        return render_template('root.html',
                                activities=activities)
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
                                container_list = "",
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

    activity_content = False
    activity_config = False
    config_container_list = []

    if activity != None:
        if activity.content != "":
            activity_content = activity.content        
        if activity.container_list != "":
            list_cont = activity.container_list.split(", ")
            for i in list_cont:
                cont = Container.query.get(i)
                if cont != None:
                    config_container_list.append(cont)

        if len(config_container_list) != 0:
            activity_config = True

        return render_template('control_activity.html', 
                                title = activity.title,
                                activity_id = activity.id,
                                activity_content = activity_content,
                                activity_config = activity_config,
                                container_list = config_container_list,
                                activity_running = activity.running,
                                )

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

        if activity.has_containers and activity.has_content:
            activity.enabled = True
            db.session.commit()

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
                    activity.running = True
                    db.session.commit()
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
                    activity.running = False
                    db.session.commit()
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
        activity.has_content = True

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




@app.route('/staff/create_config/<int:id_number>', methods = ['GET'])
def staff_create_cofig(id_number):
    activity = Activity.query.get(id_number)
    containers = Container.query.all()
    if activity != None:
        return render_template('create_config.html', 
                                title='Create Content',
                                activity_id = activity.id,
                                list_of_containers = containers)
    else:
        return render_template('404.html', 
                            message="Could not find activity.")



@app.route('/staff/add_configuration', methods = ['POST'])
def staff_submit_configuration():
    id_number = request.form['activity_id']
    container_list = request.form['container_list']

    activity = Activity.query.get(id_number)

    alert_icon = ""
    alert_color = ""
    alert_message = ""

    if activity != None:
        activity.container_list = container_list
        activity.has_containers = True

        db.session.commit()

        alert_icon = "fa fa-check"
        alert_color = "green"
        alert_message = "The activity configuration has been saved."

        return jsonify(icon=alert_icon,
                        color=alert_color,
                        content=alert_message)

    else:
        return render_template('404.html', 
                            message="Could not find activity.")



@app.route('/staff/create_container', methods=['GET', 'POST'])
def staff_create_container():

    form = NewContainerForm()
    if form.validate_on_submit():
        flash('New Container created {}'.format(
            form.name.data))

        dateNow = datetime.now()

        new_container = models.Container(
                                name = form.name.data,
                                description = form.description.data,
                                image = form.image.data,
                                expose_ports = form.ports.data,
                                )

        #add and commit the db changes
        db.session.add(new_container)
        db.session.commit()

        print("Added Container")

        return render_template('message.html', 
                            message="Added Container")

    return render_template('create_container.html', 
                            title='Create New', 
                            form=form)



                


### Supporting Functions


def get_list(activity_id):
    activity = Activity.query.get(activity_id)
    container_list = activity.container_list.split(",")

    print("activity container list {}".format(container_list))

    returning_cont_list = []
    num_ports = 0

    for c in container_list:
        print("container:".format(c))
        c_cont = Container.query.get(int(c))
        print("##### {}".format(int(c_cont.id)))
        if c_cont != None:
            new = ContainerObj(c_cont)
            print(new.container.expose_ports)
            p_l = new.container.expose_ports.split(",")
            print("list of ports: {}".format(p_l))
            for p in p_l:
                new.port_list_internal.append(int(p))
                new.desc = "Port {} on Container {}".format(p, c_cont.name)
                print(new.desc)
                num_ports += 1
            returning_cont_list.append(new)

        print("container ports: {}".format(returning_cont_list[0].port_list_internal))

    return returning_cont_list, num_ports


def get_avail_port():
    ## starting port is always 4000
    # search through from 4000 to 4999 for avail ports
    # n.b. 5000 is exclusive

    port_possible = list(range(4000, 5000))
    port_table = PortTable.query.all()
    print("Searching...")
    for a in port_table:
        port_possible.remove(a.external_port)

    if port_possible[0] != None:
        return port_possible[0]
    else:
        return False



class ContainerObj:
    port_list_internal = []
    port_list_external = []
    desc = ""

    def __init__(self, c):
        self.container = c
   