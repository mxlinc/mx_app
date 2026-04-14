"""Main Flask application entry point."""

import os
import logging
from flask import Flask
from flask_login import LoginManager

# Import configuration and database
from config import SECRET_KEY, DATABASE_URL
from db import db
from models import UserTable

# Import blueprints
from lms import lms_bp
from qb import qb_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ================== CREATE & CONFIGURE APP ================== #

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configure SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# ================== FLASK-LOGIN SETUP ================== #

login_manager = LoginManager(app)
login_manager.login_view = "lms.login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(UserTable, int(user_id))


# ================== REGISTER BLUEPRINTS ================== #

# LMS Blueprint (Learning Management System)
app.register_blueprint(lms_bp)

# QB Blueprint (Question Bank)
app.register_blueprint(qb_bp)

# ================== RUN ================== #

if __name__ == "__main__":
    app.run(debug=True)
