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
from time import sleep


#TODO design and implelent logfile commands where appripriate
logfile    = logging.getLogger('file')
logconsole = logging.getLogger('console')
logfile.debug("Debug FILE")

#Adds the specified views to the admin
#TODO Create Admin view homepage
admin.add_view(ModelView(Session, db.session))
admin.add_view(ModelView(Activity, db.session))
admin.add_view(ModelView(Container, db.session))
admin.add_view(ModelView(PortTable, db.session))

#Sets up the docker client API instances
DockerClient = docker.APIClient(base_url='unix:///var/run/docker.sock')
DClient = docker.from_env()

#Dictionary to store key: user UUID, with value: docker service ID
sessionTracker = {}
#Dictionary to store key: activity UUID, with value: docker network ID
networkTracker = {}


#Calls the exit handler when the program is halted  
atexit.register(exit_handler)



# the landing page for students in this flask app
# shows all the 'running' activites in the home template 
# so that students begin a new activity
@app.route('/', methods=['GET'])
def home():
    #get all activites which have 'running' set to true
    activities = Activity.query.filter_by(running=True).all()
    # conditional template serving
    if len(activities) > 0:
        return render_template('root.html',
                                activities=activities)
    else:
        return render_template('404.html',
                                message="There are no available activites to run right now. Ask your teacher to add some.")



# Requires the URI parameter 's' which should be and existing UUID 
# created by the /new endpoint. 
# Serves the lesson interface
@app.route('/connect', methods=['GET'])
def main_session():
    #Get the URI parameters of the session UUID
    session_id = request.args.get('s')

    #TODO Add logfile of request
    #i.e. logfile.debug("- New Connection - sUUID")

    # Handles non-UUID specified request
    if session_id == None:
        return render_template('404.html',
                                message='Specify a session')

    #get session from Session table in DB
    ses = Session.query.filter_by(unique_identifier=session_id).first()
    #check for no session found - i.e. not a valid session uuid
    if ses == None:
        return render_template('404.html',
                                message='Session does not exist')

    #TODO Add logfile of connection
    #i.e. logfile.debug("attempting to connect to: " + str(session_id))

    # Load up required values for view

    # window_list is the list of 'desktop' style windows which will be 
    # generated in the interactive 'activity workspace'
    window_list = PortTable.query.filter_by(session_id=session_id)
    # get activity from DB so can load the lesson content html field
    activity = Activity.query.get(ses.activity_id)

    return render_template('connection.html',
                        title=activity.title,
                        containers=window_list,
                        content=activity.content,
                        popout_url="/activity_workspace?s="+str(session_id))
    


# Requires the URI parameter 's' which should be and existing UUID 
# created by the /new endpoint. 
# Serves the lessons interactive workspace
@app.route('/activity_workspace', methods=['GET'])
def workspace_session():
    session_id = request.args.get('s')
    # ret error
    if session_id == None:
        return render_template('404.html',
                                message='Specify a session')

    ses = Session.query.filter_by(unique_identifier=session_id).first()
    #no session found
    if ses == None:
        return render_template('404.html',
                                message='Session does not exist')

    container_list = PortTable.query.filter_by(session_id=session_id)
    # creates a list of containers which should have a web interface window
    final_list = []
    for container in container_list:
        if container.show_as_window:
            final_list.append(container)

    # gets the activity object for html content field
    activity = Activity.query.get(ses.activity_id)
    return render_template('activity_workspace.html',
                        title=activity.title,
                        windows=final_list)
    


# Requires the URI parameter 'aid' which should be the ID of an activity which is enabled
# Creates the session, network and service then forwards the user onto /connect
@app.route('/new', methods=['GET'])
def new():
    #get date and generate a UUID for the user    
    dateNow = datetime.now()
    session_id = uuid.uuid4()

    # TODO Ask for the users name
    # TODO check UUID id unique 

    # get activty ID from URI parameter
    aid = request.args.get('aid')

    # ret error if not specified aid
    if aid == None:
        return render_template('404.html', message="Specify activity ID")

    # find the record of aid in the activitiy table of DB
    activity = Activity.query.get(aid)
    if activity == None:
        return render_template('404.html', message="Invalid activity ID")
    # check the teacher has set the activity to running
    if activity.running == False:
        return render_template('404.html', message="Activity not available")

    # split the plaintext CSV list of container IDs into list
    container_string_list = activity.container_list.split(",")
    container_instance_list = []

    # get network object
    network = generate_network(session_id, activity.id)
    # add id to tracker dict
    networkTracker[session_id] = network.id


    # iterate over each container ID in list
    index = 0
    for i in container_string_list:
        index += 1
        container, ports, titles, windowed, icons = get_properties(i)
        
        number_of_ports = len(ports)
        port_dictionary = {}
        int_port_list = []

        # iterate port to be exposed for each container
        for ref in range(len(ports)):
            # load in the properties
            internal_port = ports[ref]
            title_port = titles[ref]
            window_port = check_windowed(windowed[ref])
            icon_port = icons[ref]
            
            # get the next availible port in the system
            ext_port = get_avail_port()

            #handle cases where there are non availible
            if ext_port == False: return render_template('404.html', message="Can not run, max capacity reached")
            
            # generate a string description
            desc = "Port {} on container {}".format(internal_port, container.name)

            #add entry to dict
            port_dictionary[int(ext_port)] = int(internal_port)
            int_port_list.append(int(internal_port))

            # add entry into the portTable
            new_entry = models.PortTable(
                                session_id=str(session_id),
                                friendly_name=desc,
                                external_port=ext_port,
                                internal_port=internal_port,
                                container_id="",
                                url=get_full_url(ext_port),
                                title=title_port,
                                show_as_window=window_port,
                                icon=icon_port)
            db.session.add(new_entry)
            db.session.commit()
        

        # let the user know if the image has not been downloaded
        if (image_local(container.image) != True):
            return render_template('404.html',
                                message="There is an error with a container image. Please let your teacher know.")

        # creates a Docker comlpliant enpoint spec (port to be exposed in service)
        endpointSpec = EndpointSpec(ports=port_dictionary)
        #needs passing network in a list
        lst = []
        lst.append(str(network.name))

        #create a u-f name
        name = "session-{}-container-{}".format(str(session_id)[0:5], index)

        # create the service using the docker API
        service_id = DClient.services.create(image=str(container.image), 
                                            endpoint_spec=endpointSpec, 
                                            name=name,
                                            networks=lst)
        # add name of service to the dict
        container_instance_list.append(name)
        #TODO check for clashes in names
          
    
    # once all containers have been depolyed into the swarm
    # add entry to the sessions table in DB for tracking
    new_session = models.Session(unique_identifier=str(session_id),
                                user_number="",
                                time_created=dateNow,
                                activity_id=activity.id,
                                number_of_ports=0)
    db.session.add(new_session)
    db.session.commit()
    sessionTracker[session_id] = container_instance_list

    #logfile.debug("Added session: " + str(new_session.id))
 
    #issue redirect with uuid as parameter 's'
    query = str("/connect?" + "s=" + new_session.unique_identifier)
    return redirect(query)



# the staff homepage template
# serves all activties, regardless of state. 
# The template uses the activity object status to determine is category.
@app.route('/staff', methods=['GET'])
def staff():
    activities = Activity.query.all()
    return render_template('staff.html',
                            activities=activities)


# staff utility to create a new activity entry in the DB
# serves a flaskWTF form to validate input
@app.route('/staff/create', methods=['GET', 'POST'])
def staff_create_new():
    # generate a new form
    form = NewActivityForm()
    # if submitted and valid
    if form.validate_on_submit():
        # flash is a flask lib to show messages in web templates
        flash('New activity created {}'.format(
            form.title.data))

        #add entry to DB
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


# staff utility to control an activity directly 
# Only serves a GET method, to host the template page
# then any operators on the activity operated via a seperate POST
# method
# TODO add login security  
@app.route('/staff/activity/<int:activity_id>', methods=['GET'])
def staff_edit_activity(activity_id):
    # get the activity from DB
    activity = Activity.query.get(activity_id)
    # set check vars
    activity_content = False
    activity_config = False
    config_container_list = []

    # check activity exists
    # then load all the content and 
    # proccess list of containers  
    if activity != None:
        if activity.content != "":
            activity_content = activity.content        
        if activity.container_list != " ":
            list_cont = activity.container_list.split(", ")
            for i in list_cont:
                cont = Container.query.get(i)
                if cont != None:
                    config_container_list.append(cont)
        # if there are no containers configured, enable
        # the container designer tool 
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

    # in case of invalid activity id
    else:
        return render_template('404.html', 
                            message="Could not find the activity.")

  


# method to set the status of an activity
# Required URI Parameters:
#       activity_id:        a valid activity ID number
#       activity_action:    the action to be performed on the activity 
#         Valid options: 
#           delete        Deletes the activty
#           start         Sets the activity to running if has content and container model
#           stop          Sets the activty state to running=False if is running
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

            # TODO move readyness test to a cron style job
            # check if the container model is ready
            ready = True
            for c in container_list:
                update_container(c)
                c_instance = Container.query.get(c)
                if c_instance.is_ready != True:
                    print("Container {} not downloaded.".format(c_instance.image))
                    ready = False
                else:
                    print("Container {} is downloaded.".format(c_instance.image))
            # sets to ready in the DB
            if ready:
                activity.is_ready = True
                db.session.commit()

        # delete the activity
        if action == "delete":
            db.session.delete(activity)
            db.session.commit()

            #not a valid start/stop action
            alert_icon = "fa fa-exclamation-circle"
            alert_color = "red"
            alert_message = "The activity has been deleted."

        # otherwise check for containers and content - and warn the user
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
        # handles the instance when the images are not ready
        elif activity.is_ready == False:
            #inform the user
            alert_icon = "fa fa-exclamation-circle"
            alert_color = "red"
            alert_message = "The activities container images are not downloaded."
        else:
            #handle start activity so set to running=True
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
            # reaches here if invalid operation on the activity
            else:
                #not a valid start/stop action
                alert_icon = "fa fa-exclamation-circle"
                alert_color = "red"
                alert_message = "Not a valid operation on activity"
        # serve json response with 200
        return jsonify(icon=alert_icon,
                        color=alert_color,
                        content=alert_message)
    # handle invalid activity ID numbers
    else:
        return render_template('404.html', 
                            message="Could not find activity.")




# serves the template page to design the lesson content builder
# this page features a rich HTML block builder to design the 
# content of the lesson
# Requires:
#        id_number:     A valid ID number for an activity
@app.route('/staff/create_content/<int:id_number>', methods = ['GET'])
def staff_create_content(id_number):
    # loads and checks activity erxists
    # TODO add ability to edit the content
    #       this simply needs to load and serve the already created
    #       content - test
    activity = Activity.query.get(id_number)
    if activity != None:
        return render_template('create_content.html', 
                                title='Create Content',
                                activity_id = activity.id)
    else:
        return render_template('404.html', 
                            message="Could not find activity.")



# method to post the activity content of the lesson
# generated by lesson content designer tool
# Requires:
#        id_number:     A valid ID number for an activity
#        content:       HTML source of the generated lesson content
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



# serves the template page to design the container config for the activity
# Requires:
#        id_number:     A valid ID number for an activity
@app.route('/staff/create_config/<int:id_number>', methods = ['GET'])
def staff_create_cofig(id_number):
    activity = Activity.query.get(id_number)
    #serves all containers in a dropdown to select from
    containers = Container.query.all()
    if activity != None:
        return render_template('create_config.html', 
                                title='Create Content',
                                activity_id = activity.id,
                                list_of_containers = containers)
    else:
        return render_template('404.html', 
                            message="Could not find activity.")



# method to post the container model specification
# generated by the container designer tool
# Requires:
#        id_number:     A valid ID number for an activity
#        container_list:    A CSV list of container ID numbers
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


# method to serve the container designer tool
# also enables post method for submitting the 
# specification to the system
@app.route('/staff/create_container', methods=['GET', 'POST'])
def staff_create_container():
    # post method uses request form
    if request.method == 'POST':
        # load and check for values
        # TODO validation checks
        container_title = request.form['container_title']
        container_description = request.form['container_description']
        container_uri = request.form['container_uri']
        port_list = request.form['port_number_list']
        windowed_list = request.form['windowed_list']
        title_list = request.form['title_list']
        icon_list = request.form['icon_list']
        # 400's served for null submissions
        if (str(container_title) == ""):
            return jsonify(content="Invalid container title"), 400
        if (str(container_description) == ""):
            return jsonify(content="Invalid description"), 400
        if (str(container_uri) == ""):
            return jsonify(content="Invalid container URI"), 400
        
        # splice the lists, ensuring values
        # the lists are used to specify the parameters of each port
        # TODO move to supporting function

        p_list = port_list.split(",")
        p_list = filter(None, p_list)
        if (str(p_list) == ""):
            return jsonify(content="Invalid port list"), 400
        w_list = windowed_list.split(",")
        w_list = filter(None, w_list)
        if (str(w_list) == ""):
            return jsonify(content="Invalid windowed list"), 400
        t_list = title_list.split(",")
        t_list = filter(None, t_list)        
        if (str(t_list) ==""):
            return jsonify(content="Invalid port title list"), 400
        i_list = icon_list.split(",")
        i_list = filter(None, i_list)
        if (str(i_list) == ""):
            return jsonify(content="Invalid icon list"), 400


        # check the lists have the same number of values
        # each list indexes value corresponds to the four parameters
        # of a port - its number, show as window, window title, icon name
        v = len(p_list)
        if v == 0:
            return jsonify(content="Port configuration info is required"), 400
        if v != len(w_list):
            return jsonify(content="Missing port configuration info"), 400
        if v != len(t_list):
            return jsonify(content="Missing port configuration info"), 400
        if v != len(i_list):
            return jsonify(content="Missing port configuration info"), 400

        # checks the port number is valid
        for item in p_list:
            if item.isdigit() != True:
                return jsonify(content="Port number is not integer"), 400
        # validation for the bool of windowed
        for item in w_list:
            if item != "T" and item != "F":
                return jsonify(content="Windowed value is not T or F"), 400
        # saves the container spec
        new_container = models.Container(
                                    name = container_title,
                                    description = container_description,
                                    image = container_uri,
                                    expose_ports = port_list,
                                    port_titles = title_list,
                                    port_icons = icon_list,
                                    port_window = windowed_list
                                    )

        #add and commit the db changes
        db.session.add(new_container)
        db.session.commit()
        #redirect to download container
        return jsonify(redirect=new_container.id), 200
    # for GET serve the designer
    return render_template('create_container.html', 
                            title='Create New')


# route to serve the download progress report for a container image
# serves a page wich connects to socket.io to print messages
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




### socket.io Function
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






# SUPPORTING FUNCTIONS


# Generates a Docker Network with a name
# Requires:
#   session_id: a unique sessionID of length > 5 (from UUID)
#   activity_id: an ID number of an activity
# Returns:
#   A Docker Network Object
def generate_network(session_id, activity_id):
    # generate network name based on uuid & activity ID
    net_name = str(session_id)[0:5] + "-net-" + str(activity_id)
    # create the network
    # TODO add exception catch for name clashes
    network = DClient.networks.create(net_name, driver="overlay")
    return network



# Gets activity info
# Requires:
#   activity_id: an activity id
# Returns:
#   ports: comma seperated list of ports the container needs exposing
#   titles: comma sererated list of titles for each port
#   windowed: comma seperated list of vals True or False for show as window
#   icons: comma seperated list of icons from font-awesome
def get_properties(activity_id):
    # get container
    container = Container.query.get(activity_id)
    # TODO add check for exists
    # load properties
    ports = container.expose_ports.split(",")
    titles =container.port_titles.split(",")
    windowed = container.port_window.split(",")
    icons =container.port_icons.split(",")

    return container, ports, titles, windowed, icons



# Check if port of container needs web window in activity learning enviroment 
# also functions as validation test
# Requires:
#   str: T or F
# Returns:
#   window_port: bool
def check_windowed(val):
    if window_port == "T":
        return True
    else:
        return False




#Returns the URI the application is running on
#TODO dynamic & automatic self URI discovery
def get_full_url(port):
    return str("http://localhost:" + str(port))


#Called when the program receives shutdown
#iterates through the sessionTracker dict and stops each
#service which has been created via this application
#TODO implement checking via docker API to ensure all have been stopped
def exit_handler():
    print("\n\nShutting down...")

    allSessions = Session.query.all()

    if allSessions != None:
        for s in allSessions:
            #TODO migrate print comments to application logs
            print("Call to close: " + str(s.unique_identifier))
            for key,val in sessionTracker.items():
                lst = val
                if lst != None:
                    for c in lst:
                        print(c)
                        #Get the session object by ID
                        cont = DClient.services.get(c)
                        #Docker API command to close a Docker Service object
                        cont.remove()
                        print("Removed container service".format(c))
            #iterate and delete the network for each Session
            for key,val in networkTracker.items():
                net = DClient.networks.get(val)
                net.remove()
                print("Removed network".format(net.id))

            #Deletes the entry from the Session DB table
            db.session.delete(s)
        db.session.commit()

    all_rows = PortTable.query.all()
    #Delete all the entries in the portTable
    #TODO implement dynamic checking that the port is now free
    for r in all_rows:
        db.session.delete(r)
    db.session.commit()
    


# Checks if an image exists locally
# Requires:
#   image_name: string, a name of a docker image
# Returns:
#   bool:       true if image exists locally, false otherwise
def image_local(image_name):
    list_images = DClient.images.list()
    #gets list of images
    # checks for any version, thus, removes tag
    # e.g. ':latest' but checks to avoid removing 
    # URI with port, ie. local repo '10.0.0.10:5000/imgae:tag'
    # would have ':5000/imgae:tag' removed without this check
    for i in list_images:
        tags = i.tags
        for t in tags:
            if image_name == t:
                return True
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




# function changes the status of the container to isReady=True if
# the container is ready to be run
# TODO change to cron style job
# Requires:
#   container_id:       int, the id of a container (from DB id)
#                       the container should be ready to run, but 
#                       this function checks before changing the status
# Returns:
#   none
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




# gets the next availilb eport in the system
# done so by checking the PortTable for next avilible entry
# Requires:
#   none
# Returns:
#   integer:       port number if on is available, false otherwise
# TODO implement dynamic checking to ensure port if free on host system
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

