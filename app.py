


from datetime import timedelta
import io
import os
from flask import Flask, render_template, request, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import pickle
from werkzeug.security import generate_password_hash, check_password_hash


def get_database_url():
    database_url = os.getenv('DATABASE_URL', 'sqlite:///test.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return database_url


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'change-this-in-production')
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)




class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # relationship for storing predictions (we will use later)
    predictions = db.relationship('Prediction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    age = db.Column(db.Float)
    sleeping_hours = db.Column(db.Float)
    result = db.Column(db.String(50))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Create tables
with app.app_context():
    db.create_all()

pickle_in = open("classifier.pkl", "rb")
rf = pickle.load(pickle_in)

@app.before_request
def make_session_permanent():
    """Make session permanent for authenticated users so timeout applies."""
    if 'user_id' in session:
        session.permanent = True
    else:
        session.permanent = False

def predict_depression(Age, Sleepinghours, Workhours, Weeks_of_Pregnancy, Healthproblems, Desiredpregnancy,
                       Maritalstatus, Family_history_of_mentalillness, Weight):
    prediction = rf.predict([[Age, Sleepinghours, Workhours, Weeks_of_Pregnancy, Healthproblems, Desiredpregnancy,
                               Maritalstatus, Family_history_of_mentalillness, Weight]])
    return prediction


def generate_pdf_report(input_features, result):
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)

    c.drawString(100, 750, "Perinatal Disease Predictor Report")
    c.drawString(100, 730, "-------------------------------------------")
    c.drawString(100, 710, "Patients information:")
    c.drawString(100, 690, f"Age: {input_features['Age']}")
    c.drawString(100, 670, f"Sleeping Hours: {input_features['Sleepinghours']}")
    c.drawString(100, 650, f"Work Hours: {input_features['Workhours']}")
    c.drawString(100, 630, f"Weeks of Pregnancy: {input_features['Weeks_of_Pregnancy']}")
    c.drawString(100, 610, f"Health Problems (0 for NO or 1 for YES): {input_features['Healthproblems']}")
    c.drawString(100, 590, f"Desired Pregnancy (0 for NO or 1 for YES): {input_features['Desiredpregnancy']}")
    c.drawString(100, 570, f"Marital Status (0 for NO or 1 for YES): {input_features['Maritalstatus']}")
    c.drawString(100, 550, f"Family History of Mental Illness (0 for NO or 1 for YES): {input_features['Family_history_of_mentalillness']}")
    c.drawString(100, 530, f"Weight: {input_features['Weight']}")
    c.drawString(100, 510, "-------------------------------------------")
    c.drawString(100, 490, "Result:")

    if result[0] == 0:
        c.drawString(100, 470, "Not depression")
    elif result[0] == 1:
        c.drawString(100, 470, "Depression")
    else:
        c.drawString(100, 470, str(result[0]))

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact_us.html')



@app.route('/consult')
def feedback():
    return render_template('consult.html')

@app.route('/check-session')
def check_session():
    if not app.debug:
        return "Not Found", 404
    return str(session)


@app.route('/predict', methods=['POST'])
def predict_handler():
    
    #  Check login first
    if 'user_id' not in session:
        return redirect(url_for('login'))

    input_features = {
        'Age': float(request.form.get('Age', 0)),
        'Sleepinghours': float(request.form.get('Sleepinghours', 0)),
        'Workhours': float(request.form.get('Workhours', 0)),
        'Weeks_of_Pregnancy': float(request.form.get('Weeks_of_Pregnancy', 0)),
        'Healthproblems': float(request.form.get('Healthproblems', 0)),
        'Desiredpregnancy': float(request.form.get('Desiredpregnancy', 0)),
        'Maritalstatus': float(request.form.get('Maritalstatus', 0)),
        'Family_history_of_mentalillness': float(request.form.get('Family_history_of_mentalillness', 0)),
        'Weight': float(request.form.get('Weight', 0))
    }

    result = predict_depression(
        input_features['Age'],
        input_features['Sleepinghours'],
        input_features['Workhours'],
        input_features['Weeks_of_Pregnancy'],
        input_features['Healthproblems'],
        input_features['Desiredpregnancy'],
        input_features['Maritalstatus'],
        input_features['Family_history_of_mentalillness'],
        input_features['Weight']
    )

    # 🔥 Save prediction in DB
    new_prediction = Prediction(
        age=input_features['Age'],
        sleeping_hours=input_features['Sleepinghours'],
        result="Depression" if result[0] == 1 else "Not Depression",
        user_id=session['user_id']
    )

    db.session.add(new_prediction)
    db.session.commit()

    pdf_buffer = generate_pdf_report(input_features, result)
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=False, download_name='report.pdf')


@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return 'Username already exists.'

        new_user = User(username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            return 'Invalid username or password.'

    return render_template('login.html')

@app.route("/logout")
def logout():
    """Logout Form"""
    session.clear()
    response = redirect(url_for('home'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == "__main__":
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
