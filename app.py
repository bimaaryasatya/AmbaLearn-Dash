from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, distinct, UniqueConstraint
from datetime import datetime, timedelta
import random
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Globals for dummy data ---
DUMMY_COURSES = []

def load_dummy_courses():
    """Loads course data from the JSON file."""
    global DUMMY_COURSES
    try:
        with open('course_example.json', 'r') as f:
            # Wrap the single course object in a list to simulate multiple courses
            DUMMY_COURSES = [json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading dummy course data: {e}")
        DUMMY_COURSES = []

def save_dummy_courses():
    """Saves the first dummy course back to the JSON file."""
    global DUMMY_COURSES
    if DUMMY_COURSES:
        try:
            with open('course_example.json', 'w') as f:
                # Save only the first course, assuming a 1-to-1 mapping with the file
                json.dump(DUMMY_COURSES[0], f, indent=2)
        except IOError as e:
            print(f"Error saving dummy course data: {e}")

# --- Database Models ---
class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True)
    organization = db.relationship('Organization', backref=db.backref('users', lazy=True))

    def __repr__(self):
        return f'<User {self.username}>'

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('prompts', lazy=True))

    def __repr__(self):
        return f'<Prompt {self.id}>'

class DailyActiveUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'date', name='_user_date_uc'),)

def populate_data():
    """Populates the database with dummy data."""
    # --- Create Organizations and Courses ---
    org_names = ['Org A', 'Org B', 'Org C', 'Org D', 'Org E']
    course_names = ['Intro to AI', 'Advanced Machine Learning', 'Data Science 101', 'Python for Beginners', 'Natural Language Processing']
    
    for name in org_names:
        if not Organization.query.filter_by(name=name).first():
            db.session.add(Organization(name=name))
            
    for name in course_names:
        if not Course.query.filter_by(name=name).first():
            db.session.add(Course(name=name))
    db.session.commit()

    # --- Create Users ---
    orgs = Organization.query.all()
    users_to_create = []
    for i in range(100):
        created_date = datetime.utcnow() - timedelta(days=random.randint(0, 29))
        last_seen_delta = timedelta(days=random.randint(0, (datetime.utcnow() - created_date).days))
        last_seen_date = created_date + last_seen_delta
        users_to_create.append(User(username=f'user{i}', created_at=created_date, last_seen=last_seen_date, organization_id=random.choice(orgs).id))

    db.session.bulk_save_objects(users_to_create, return_defaults=True)
    db.session.commit()

    # --- Create Prompts and Daily Active Users ---
    prompts_to_create = []
    daily_active_users_to_add = set()
    users = User.query.all()
    for user in users:
        for _ in range(random.randint(5, 50)):
            if (datetime.utcnow() - user.created_at).days > 0:
                prompt_date_delta = timedelta(days=random.randint(0, (datetime.utcnow() - user.created_at).days))
                prompt_date = user.created_at + prompt_date_delta
                prompts_to_create.append(Prompt(user_id=user.id, prompt_text=f'This is a sample prompt by {user.username}', created_at=prompt_date))
                # Add to set for daily active users
                daily_active_users_to_add.add((user.id, prompt_date.date()))

    db.session.bulk_save_objects(prompts_to_create)
    
    # Create DailyActiveUser records
    for user_id, date in daily_active_users_to_add:
        db.session.add(DailyActiveUser(user_id=user_id, date=date))
        
    db.session.commit()

# --- Routes ---
@app.route('/')
def overview():
    # --- Analytics for Cards ---
    total_organizations = Organization.query.count()
    total_courses = Course.query.count()
    total_prompts_count = Prompt.query.count()
    total_users_count = User.query.count()

    # --- Data for Charts (last 30 days) ---
    days_range = [datetime.utcnow().date() - timedelta(days=i) for i in range(30)]
    days_range.reverse()
    
    # Prompts per day
    prompts_per_day_query = db.session.query(func.date(Prompt.created_at), func.count(Prompt.id)).filter(Prompt.created_at >= datetime.utcnow() - timedelta(days=30)).group_by(func.date(Prompt.created_at)).all()
    prompts_per_day = dict(prompts_per_day_query)
    prompt_counts = [prompts_per_day.get(day.strftime('%Y-%m-%d'), 0) for day in days_range]

    # New users per day
    new_users_per_day_query = db.session.query(func.date(User.created_at), func.count(User.id)).filter(User.created_at >= datetime.utcnow() - timedelta(days=30)).group_by(func.date(User.created_at)).all()
    new_users_per_day = dict(new_users_per_day_query)
    new_user_counts = [new_users_per_day.get(day.strftime('%Y-%m-%d'), 0) for day in days_range]
    
    # Active users per day (users who made a prompt)
    active_users_per_day_query = db.session.query(DailyActiveUser.date, func.count(DailyActiveUser.user_id)).filter(DailyActiveUser.date >= datetime.utcnow().date() - timedelta(days=30)).group_by(DailyActiveUser.date).all()
    active_users_per_day = {date.strftime('%Y-%m-%d'): count for date, count in active_users_per_day_query}
    active_user_counts = [active_users_per_day.get(day.strftime('%Y-%m-%d'), 0) for day in days_range]


    chart_labels = [day.strftime('%m-%d') for day in days_range]

    return render_template('index.html', 
                           total_organizations=total_organizations,
                           total_courses=total_courses,
                           total_prompts_count=total_prompts_count,
                           total_users_count=total_users_count,
                           chart_labels=chart_labels,
                           prompt_counts=prompt_counts,
                           new_user_counts=new_user_counts,
                           active_user_counts=active_user_counts)


# --- Models Route ---
@app.route('/models')
def models():
    return render_template('models.html')

# --- Course Routes ---
@app.route('/courses')
def courses():
    return render_template('courses.html', courses=DUMMY_COURSES)

@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    course = None
    # Adjust index for 1-based ID from URL to 0-based list index
    course_index = course_id - 1

    if course_id > 0 and course_id <= len(DUMMY_COURSES):
        course = DUMMY_COURSES[course_index]

    if request.method == 'POST':
        # Reconstruct the course object from form data
        new_course_data = {
            "course_title": request.form.get('course_title'),
            "description": request.form.get('description'),
            "difficulty": request.form.get('difficulty'),
            "steps": []
        }

        # Process steps
        step_index = 0
        while f'step_title_{step_index}' in request.form:
            content_outline = request.form.get(f'step_content_{step_index}', '').split(',')
            new_step = {
                "step_number": step_index + 1,
                "title": request.form.get(f'step_title_{step_index}'),
                "objective": request.form.get(f'step_objective_{step_index}'),
                "content_outline": [item.strip() for item in content_outline]
            }
            new_course_data["steps"].append(new_step)
            step_index += 1
        
        # If it's a new course, append it. Otherwise, update existing.
        if course_id == 0:
            DUMMY_COURSES.append(new_course_data)
        else:
            DUMMY_COURSES[course_index] = new_course_data

        save_dummy_courses()
        return redirect(url_for('courses'))
        
    return render_template('edit_course.html', course=course, course_id=course_id)


# --- Organization Routes ---
@app.route('/organizations')
def organizations():
    all_orgs = Organization.query.all()
    return render_template('organizations.html', organizations=all_orgs)

@app.route('/add_organization', methods=['POST'])
def add_organization():
    org_name = request.form['organization_name']
    if org_name:
        new_org = Organization(name=org_name)
        db.session.add(new_org)
        db.session.commit()
    return redirect(url_for('organizations'))

@app.route('/edit_organization/<int:org_id>', methods=['GET', 'POST'])
def edit_organization(org_id):
    org = Organization.query.get_or_404(org_id)
    if request.method == 'POST':
        org.name = request.form['organization_name']
        db.session.commit()
        return redirect(url_for('organizations'))
    return render_template('edit_organization.html', org=org)

@app.route('/delete_organization/<int:org_id>')
def delete_organization(org_id):
    org = Organization.query.get_or_404(org_id)
    db.session.delete(org)
    db.session.commit()
    return redirect(url_for('organizations'))

# --- User Routes ---
@app.route('/users')
def users():
    all_users = User.query.all()
    all_orgs = Organization.query.all()
    return render_template('users.html', users=all_users, organizations=all_orgs)

@app.route('/add_user', methods=['POST'])
def add_user():
    username = request.form['username']
    org_id = request.form.get('organization_id')
    if username:
        new_user = User(username=username, organization_id=org_id if org_id else None)
        db.session.add(new_user)
        db.session.commit()
    return redirect(url_for('users'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    all_orgs = Organization.query.all()
    if request.method == 'POST':
        user.username = request.form['username']
        user.organization_id = request.form.get('organization_id')
        db.session.commit()
        return redirect(url_for('users'))
    return render_template('edit_user.html', user=user, organizations=all_orgs)

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/feedback')
def feedback():
    """Renders the feedback page with placeholder data."""
    # Placeholder data
    feedback_data = [
        {'user': 'user1', 'comment': 'This course was great!', 'course_name': 'Intro to AI', 'sentiment': 'Good'},
        {'user': 'user2', 'comment': 'I did not like this course.', 'course_name': 'Advanced Machine Learning', 'sentiment': 'Bad'},
        {'user': 'user3', 'comment': 'The instructor was very clear.', 'course_name': 'Data Science 101', 'sentiment': 'Good'},
        {'user': 'user4', 'comment': 'The course content was outdated.', 'course_name': 'Python for Beginners', 'sentiment': 'Bad'},
    ]
    return render_template('feedback.html', feedback_data=feedback_data)

if __name__ == '__main__':
    with app.app_context():
        # Since the user said they dropped the tables, we will always recreate and seed.
        # For production, you'd want a more robust migration system.
        print("Dropping all tables and recreating them...")
        db.drop_all()
        db.create_all()
        populate_data()
        print("Database is ready.")
        load_dummy_courses()
    app.run(debug=True)
