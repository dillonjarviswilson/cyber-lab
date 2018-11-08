from app import db

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True, index=True)
    user_number = db.Column(db.Integer)
    unique_identifier = db.Column(db.String(300))
    ap_address = db.Column(db.String(30))
    client_address = db.Column(db.String(30))
    pos_address = db.Column(db.String(30))
    time_created = db.Column(db.DateTime)


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
    config = db.Column(db.String(1000000))
    number_of_students = db.Column(db.Integer)
    number_of_containers = db.Column(db.Integer)


