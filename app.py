"""Main Flask application entry point."""

import os
import logging
from flask import Flask
from flask_login import LoginManager
from flask import send_from_directory

# Import configuration and database
from config import SECRET_KEY, DATABASE_URL, PACKAGE_DATA_PATH, LATEX_RENDERER, QIMAGE_PATH
from db import db
from models import UserTable

# Import blueprints
from lms import lms_bp
from qb import qb_bp, question_bp

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
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,   # test connection before use; discard if dead
    "pool_recycle": 1800,    # recycle connections after 30 min
}
app.config["LATEX_RENDERER"] = LATEX_RENDERER

# Initialize database
db.init_app(app)

# ================== FLASK-LOGIN SETUP ================== #

login_manager = LoginManager(app)
login_manager.login_view = "lms.login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(UserTable, int(user_id))


# ================== REGISTER BLUEPRINTS ================== #

# ==================== direct path for testing ==================== #

from flask import send_from_directory, redirect

@app.route('/pkg/<pkg_name>')
def serve_pkg_redirect(pkg_name):
    return redirect(f'/pkg/{pkg_name}/')

@app.route('/pkg/<pkg_name>/')
def serve_pkg(pkg_name):
    return send_from_directory(os.path.join(PACKAGE_DATA_PATH, pkg_name), 'index.html')

@app.route('/pkg/<pkg_name>/<path:filename>')
def serve_pkg_files(pkg_name, filename):
    return send_from_directory(os.path.join(PACKAGE_DATA_PATH, pkg_name), filename)


@app.route('/qimage/<filename>')
def serve_qimage(filename):
    return send_from_directory(QIMAGE_PATH, filename)


# LMS Blueprint (Learning Management System)
app.register_blueprint(lms_bp)

# Question Blueprint
app.register_blueprint(question_bp)

# QB Blueprint (Question Bank / Quiz Management)
app.register_blueprint(qb_bp)

# ================== RUN ================== #

if __name__ == "__main__":
    app.run(debug=True)
