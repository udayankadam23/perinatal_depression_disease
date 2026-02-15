


from flask import Flask, render_template, request, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import pickle
from sqlalchemy.orm.exc import NoResultFound

app = Flask(__name__)
app.secret_key = 'helloworldhelloworld'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class User(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))

    def __init__(self, username, password):
        self.username = username
        self.password = password

# Create tables
with app.app_context():
    db.create_all()

pickle_in = open("classifier.pkl", "rb")
rf = pickle.load(pickle_in)

def predict_depression(Age, Sleepinghours, Workhours, Weeks_of_Pregnancy, Healthproblems, Desiredpregnancy,
                       Maritalstatus, Family_history_of_mentalillness, Weight):
    prediction = rf.predict([[Age, Sleepinghours, Workhours, Weeks_of_Pregnancy, Healthproblems, Desiredpregnancy,
                               Maritalstatus, Family_history_of_mentalillness, Weight]])
    return prediction

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

@app.route('/predict', methods=['POST'])
def predict_handler():
    if request.method == 'POST':
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

        result = predict_depression(input_features['Age'], input_features['Sleepinghours'],
                                    input_features['Workhours'], input_features['Weeks_of_Pregnancy'],
                                    input_features['Healthproblems'], input_features['Desiredpregnancy'],
                                    input_features['Maritalstatus'], input_features['Family_history_of_mentalillness'],
                                    input_features['Weight'])

        filename = 'report.pdf'
        generate_pdf_report(input_features, result, filename)
        return send_file(filename, as_attachment=False)

def generate_pdf_report(input_features, result, filename):
    
    c = canvas.Canvas(filename, pagesize=letter)

    
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







@app.route('/register/', methods=['GET', 'POST'])
def register():
    """Register Form"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print("Username already exists. Please choose a different username.")
            return 'Username already exists. Please choose a different username.'
        
        
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        print(f"User {username} registered successfully.")
        return redirect(url_for('login'))

    return render_template('register.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login Form"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            
            user = User.query.filter_by(username=username, password=password).one()
            session['logged_in'] = True
            return redirect(url_for('home'))
        except NoResultFound:
            return 'User not found or incorrect password.'

    return render_template('login.html')

@app.route("/logout")
def logout():
    """Logout Form"""
    session['logged_in'] = False
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
