import os
import fileinput
from flask import Flask, abort, request, jsonify, g, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from passlib.apps import custom_app_context as pwd_context


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True

db = SQLAlchemy(app)
auth = HTTPBasicAuth()


class User(db.Model):
	__tablename__='users'
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(32), index=True)
	password_hash = db.Column(db.String(64))
	location_id = db.Column(db.Integer, db.ForeignKey("rooms.id"))
	location = db.relationship("Room", back_populates="players")

	def hash_password(self, password):
		self.password_hash = pwd_context.encrypt(password)

	def verify_password(self, password):
		return pwd_context.verify(password, self.password_hash)

class Room(db.Model):
	__tablename__='rooms'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), index=True)
	description = db.Column(db.Text)
	players = db.relationship("User", order_by=User.id, back_populates="location")
	exits = db.relationship("Portal", back_populates="source", foreign_keys="Portal.source_id")
	entrances = db.relationship("Portal", back_populates="destination", foreign_keys="Portal.destination_id")

class Portal(db.Model):
	__tablename__='portals'
	id = db.Column(db.Integer, primary_key=True)
	source_id = db.Column(db.Integer, db.ForeignKey("rooms.id"))
	source = db.relationship("Room", back_populates="exits", foreign_keys="Portal.source_id")
	direction = db.Column(db.String(16))
	destination_id = db.Column(db.Integer, db.ForeignKey("rooms.id"))
	destination = db.relationship("Room", back_populates="entrances", foreign_keys="Portal.destination_id")


@auth.verify_password
def verify_password(username, password):
	user = User.query.filter_by(username=username).first()
	if not user or not user.verify_password(password):
		return False
	g.user = user
	return True

@app.route('/users', methods=['POST'])
def create_user():
	username = request.json.get('username')
	password = request.json.get('password')
	if username is None or password is None:
		abort(400)
	if User.query.filter_by(username=username).first() is not None:
		abort(400)
	user = User(username=username)
	user.hash_password(password)
	user.location = Room.query.filter_by(id=1).first()
	db.session.add(user)
	db.session.commit()
	return(jsonify({'username': user.username}), 201, {'Location': url_for('get_username', id=user.id, _external=True)})

@app.route('/users/<int:id>')
def get_username(id):
	user= User.query.get(id)
	if not user:
		abort(400)
	return jsonify({'username': user.username, 'location':user.location.name})

@app.route('/users/<string:username>')
def get_userid(username):
	user = User.query.filter_by(username=username).first()
	if not user:
		abort(400)
	return jsonify({'id': user.id})

@app.route('/look')
@auth.login_required
def get_current_location():
	occupants=[]
	for u in g.user.location.players:
		occupants.append(u.username)
	return jsonify({'location_id': g.user.location.id, 'location_name': g.user.location.name, 'location_description': g.user.location.description, 'users': occupants})

@app.route('/move', methods=['POST'])
@auth.login_required
def move():
	user = g.user
	direction = request.json.get('direction')
	if direction is None:
		abort(400)

	# check exits - if possible, move there

	return (jsonify({'current_location': user.location_id}), 200, {'Look': url_for('get_current_location', _external=True)})

@app.route('/')
def hello():
    return "Welcome to PyMUD.  Login to continue."

def load_map_from_text():
	with open('map.txt') as f:
		content = f.readlines()
		for line in content:
			tokens = line.split(',')
			if tokens[0] == "Room":
				room = Room(name=tokens[1].strip(' \n'), description=tokens[2].strip(' \n'))
				db.session.add(room)
				db.session.commit()
			elif tokens[0] == "Portal":
				portal = Portal(source=Room.query.filter_by(name=tokens[1].strip(' \n')).first(), direction=tokens[2].strip(' \n'), destination=Room.query.filter_by(name=tokens[3].strip(' \n')).first())
				db.session.add(portal)
				db.session.commit()

if __name__ == "__main__":
	if not os.path.exists('db.sqlite'):
		db.create_all()
	if not Room.query.filter_by(id=1).first():
		load_map_from_text()
	app.run(host='0.0.0.0')