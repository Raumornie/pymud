import os
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
	room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"))
	room = db.relationship("Room", back_populates="players")

	def hash_password(self, password):
		self.password_hash = pwd_context.encrypt(password)

	def verify_password(self, password):
		return pwd_context.verify(password, self.password_hash)

class Room(db.Model):
	__tablename__='rooms'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64))
	description = db.Column(db.Text)
	players = db.relationship("User", order_by=User.id, back_populates="room")


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
	db.session.add(user)
	db.session.commit()
	return(jsonify({'username': user.username}), 201, {'Location': url_for('get_user', id=user.id, _external=True)})

@app.route('/users/<int:id>')
def get_username(id):
	user= User.query.get(id)
	if not user:
		abort(400)
	return jsonify({'username': user.username})

@app.route('/users/<string:username>')
def get_userid(username):
	user = User.query.filter_by(username=username).first()
	if not user:
		abort(400)
	return jsonify({'id': user.id})

@app.route('/resource')
@auth.login_required
def get_resource():
	return jsonify({'data': 'Hello, %s' % g.user.username})

@app.route('/')
def hello():
    return "Hello World!"

if __name__ == "__main__":
	if not os.path.exists('db.sqlite'):
		db.create_all()
	if not Room.query.filter_by(id=1).first():
		room = Room(name="The Entrance", description="You are at the entrance to a very creepy dungeon.  You feel as though coming here may not have been a great idea.")
	app.run(host='0.0.0.0')