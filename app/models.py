from app import db

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True, index=True)
    user_number = db.Column(db.Integer)
    unique_identifier = db.Column(db.String(300))
    time_created = db.Column(db.DateTime)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    number_of_ports = db.Column(db.Integer)
    container_id_list = db.Column(db.String(5000))


class PortTable(db.Model):
    id = db.Column(db.Integer, primary_key=True, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'),
        nullable=False)
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'),
        nullable=False)
    friendly_name = db.Column(db.String(300))
    internal_port = db.Column(db.Integer)
    external_port = db.Column(db.Integer)
    url = db.Column(db.String(300))


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True, index=True)
    enabled = db.Column(db.Boolean)
    is_ready = db.Column(db.Boolean)
    running = db.Column(db.Boolean)
    title = db.Column(db.String(40))
    description = db.Column(db.String(300))
    category = db.Column(db.String(300))
    has_content = db.Column(db.Boolean)
    has_containers = db.Column(db.Boolean)
    time_created = db.Column(db.DateTime)
    content = db.Column(db.String(1000000))
    number_of_students = db.Column(db.Integer)
    number_of_containers = db.Column(db.Integer)
    container_list = db.Column(db.String(5000))


class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True, index=True)
    name = db.Column(db.String(50))
    description = db.Column(db.String(5000))
    image = db.Column(db.String(500))
    expose_ports = db.Column(db.String(500))


