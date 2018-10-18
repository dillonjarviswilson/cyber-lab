from app import db

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True, index=True)
    user_number = db.Column(db.Integer)
    unique_identifier = db.Column(db.String(300))
    ap_address = db.Column(db.String(30))
    client_address = db.Column(db.String(30))
    pos_address = db.Column(db.String(30))
    time_created = db.Column(db.DateTime)

