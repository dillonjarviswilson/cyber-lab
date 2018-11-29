from app import app, db, models, setup, socketio, admin
from flask_socketio import send, emit
from flask import render_template, url_for, redirect, flash, request
from datetime import datetime
from flask_admin.contrib.sqla import ModelView
from app.models import Session, Activity, Container, PortTable
from app.forms import NewActivityForm, NewContainerForm
from sqlalchemy import desc, tuple_
import docker
from docker import errors
from docker.types import EndpointSpec
from docker.utils import create_host_config
import logging, logging.config, uuid
import atexit
from flask import jsonify
import subprocess
import json


logfile    = logging.getLogger('file')
logconsole = logging.getLogger('console')

logfile.debug("Debug FILE")

admin.add_view(ModelView(Session, db.session))
admin.add_view(ModelView(Activity, db.session))
admin.add_view(ModelView(Container, db.session))
admin.add_view(ModelView(PortTable, db.session))

DockerClient = docker.APIClient(base_url='unix:///var/run/docker.sock')
DClient = docker.from_env()
sessionTracker = {}
networkTracker = {}

def get_full_url(port):
    return str("10.0.0.10:" + str(port))

def exit_handler():
    print("\n\nShutting down...")

    allSessions = Session.query.all()

    if allSessions != None:
        for s in allSessions:
            print("Call to close: " + str(s.unique_identifier))
            
            for key,val in sessionTracker.items():
                lst = val
                if lst != None:
                    for c in lst:
                        print(c)
                        cont = DClient.services.get(c)
                        cont.remove()
                        print("Removed container service".format(c))

            for key,val in networkTracker.items():
                net = DClient.networks.get(val)
                net.remove()
                print("Removed network".format(net.id))

            db.session.delete(s)
        db.session.commit()

    all_rows = PortTable.query.all()

    for r in all_rows:
        db.session.delete(r)
    db.session.commit()
    


atexit.register(exit_handler)



@app.route('/connect', methods=['GET'])
def main_session():

    logfile.debug("- New Connection -")

    session_id = request.args.get('s')
    container = request.args.get('c')

    if session_id == None:
        return render_template('404.html',
                                message='Specify a session')

    if container == None:
        return render_template('404.html',
                                message='No container ID specified')

    ses = Session.query.filter_by(unique_identifier=session_id).first()
    #no session found
    if ses == None:
        return render_template('404.html',
                                message='Session does not exsist')


    logfile.debug("attempting to connect to: " + str(session_id))
    #port_list = PortTable.query.filter_by(session_id=session_id)
    container_list = PortTable.query.filter_by(session_id=session_id)

    #for entry in port_list:

    return render_template('connection.html',
                        containers=container_list)
    
    


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



    container_string_list = activity.container_list.split(",")
    container_instance_list = []


    net_name = str(session_id)[0:5] + "-net-" + str(activity.id)
    network = DClient.networks.create(net_name, driver="overlay")

    networkTracker[session_id] = network.id

    print("new_network {}".format(network.id))


    index = 0
    for i in container_string_list:
        index += 1
        container = Container.query.get(i)

        print("Container: {} \tports: {}".format(container.name, str(container.expose_ports)))

        ports = container.expose_ports.split(",")
        number_of_ports = len(ports)
        port_dictionary = {}
        int_port_list = []


        for internal_port in ports:

            ext_port = get_avail_port()
            if ext_port == False: return render_template('404.html', message="Can not run, max capacity reached")
                
            desc = "Port {} on container {}".format(internal_port, container.name)

            port_dictionary[int(ext_port)] = int(internal_port)
            int_port_list.append(int(internal_port))

            new_entry = models.PortTable(
                                session_id=str(session_id),
                                friendly_name=desc,
                                external_port=ext_port,
                                internal_port=internal_port,
                                container_id="",
                                url=get_full_url(ext_port))

            db.session.add(new_entry)
            db.session.commit()
        

        if (image_local(container.image) != True):
            return render_template('404.html',
                                message="There is an error with a container image. Please let your teacher know.")



        #container_config = DockerClient.create_host_config(
         #   port_bindings=port_dictionary)

        #docker_container_instance = DockerClient.create_container(
         #       image=str(container.image), 
         #       ports=int_port_list,
         #       host_config=container_config,
         ##       detach=True,
        #)

        endpointSpec = EndpointSpec(ports=port_dictionary)

        lst = []
        lst.append(str(network.name))

        name = "session-{}-container-{}".format(str(session_id)[0:5], index)
        
        #task_tmpl = docker.types.TaskTemplate(docker_container_instance['Id'])
        print("Network id = {}".format(network.name))

        service_id = DClient.services.create(image=str(container.image), 
                                            endpoint_spec=endpointSpec, 
                                            name=name,
                                            networks=lst)

    

        print("NAME: {}".format(service_id))

        #DockerClient.start(docker_container_instance['Id'])

        container_instance_list.append(name)
          
        print("Container Name: {} \tPorts: {}".format(
            str(container.image),
            str(port_dictionary)
        ))
    

    new_session = models.Session(unique_identifier=str(session_id),
                                user_number="",
                                time_created=dateNow,
                                activity_id=activity.id,
                                number_of_ports=0)

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
                                container_list = " ",
                                description = form.description.data,
                                enabled = False,
                                is_ready = False,
                                number_of_students = 0,
                                number_of_containers = 0)

        #add and commit the db changes
        db.session.add(new_activity)
        db.session.commit()

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
        if activity.container_list != " ":
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

            container_list = activity.container_list.split(',')

            #assume ready, check if is
            ready = True
            for c in container_list:
                update_container(c)
                c_instance = Container.query.get(c)
                if c_instance.is_ready != True:
                    print("Container {} not downloaded.".format(c_instance.image))
                    ready = False
                else:
                    print("Container {} is downloaded.".format(c_instance.image))
            
            if ready:
                activity.is_ready = True
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
        elif activity.is_ready == False:
            #inform the user
            alert_icon = "fa fa-exclamation-circle"
            alert_color = "red"
            alert_message = "The activities container images are not downloaded."
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

        image_name = form.image.data
        print("getting image {}".format(image_name))

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

        return redirect('/staff/container_progress?cont=' + str(new_container.id))

    return render_template('create_container.html', 
                            title='Create New', 
                            form=form)



@app.route('/staff/container_progress', methods=['GET'])
def staff_container_progress():

    cont_id = request.args.get('cont')

    new_container = Container.query.get(cont_id)

    if new_container:
        t = "Downloading " + str(new_container.image)
        return render_template('downloading_container.html', 
                                title=t,
                                cont_id=str(cont_id)) 
    else: return render_template('404.html', message="Could not locate container") 




### socket.io Functions
@socketio.on('get_progress')
def handle_my_custom_event(cont_id):
    
    container = Container.query.get(cont_id)
    print(container)
    if container:
        try:
            for line in DockerClient.pull(container.image, stream=True):
                emit('progress_response', line)
            line = '{"complete": "The container has been setup"}'
            emit('progress_response', line)
            container.is_ready = True
            db.session.commit()

        except errors.APIError as api_error:
            print(api_error)
            print("removed container model {}".format(container.name))
            db.session.delete(container)
            db.session.commit()
    else:
        line = '{"error": "The container has been removed"}'
        emit('progress_response', line)






### Supporting Functions


def get_list(activity_id):
    activity = Activity.query.get(activity_id)
    container_list = activity.container_list.split(",")

    #print("activity container list {}".format(container_list))

    returning_cont_list = []
    num_ports = 0

    for i in container_list:
        container = Container.query.get(i)

        print("Container: {} \tports: {}".format(container.name, str(container.expose_ports)))

        ports = container.expose_ports.split(",")
        
        print(ports)

    return returning_cont_list, num_ports


def get_avail_port():
    ## starting port is always 4000
    # search through from 4000 to 4999 for avail ports
    # n.b. 5000 is exclusive

    port_possible = list(range(4001, 5000))
    port_table = PortTable.query.all()

    for a in port_table:
        port_possible.remove(a.external_port)
    
    if len(port_possible) != 0:
        return port_possible[0]
    else:
        return False

def update_container(container_id):
    container = Container.query.get(container_id)
    print(container)
    if container:
        if container.is_ready != True:
            try:
                DockerClient.pull(container.image, stream=False)
                flash('Image {} pulled for container {}'.format(container.image, container.name))
                container.is_ready = True
                db.session.commit()

            except errors.APIError as api_error:
                print(api_error)
                #print("removed container model {}".format(container.name))
                flash('Image {} could not be pulled for container {}'.format(container.image, container.name))
                #db.session.delete(container)
                #db.session.commit()
    else:
        line = '{"error": "The container has been removed"}'
        emit('progress_response', line)


def image_local(image_name):
    list_images = DClient.images.list()

    for i in list_images:
        tags = i.tags
        for t in tags:
            t_segmented = t.split(':')
            full_base = ""
            for count in range(0, len(t_segmented)-1):
                if count != 0:
                    full_base += ":"
                full_base += t_segmented[count]
            print("Checking Tag {}".format(full_base))
            if image_name == full_base:
                return True
    return False


class ContainerObj:
    port_list_internal = []
    port_list_external = []
    desc = ""

    def __init__(self, c):
        self.container = c
   