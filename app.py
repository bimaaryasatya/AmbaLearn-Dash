from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, distinct, UniqueConstraint
from datetime import datetime, timedelta
import pymysql
import random

pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/ambalearn'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    prompts_per_day = {date.strftime('%Y-%m-%d'): count for date, count in prompts_per_day_query}
    prompt_counts = [prompts_per_day.get(day.strftime('%Y-%m-%d'), 0) for day in days_range]

    # New users per day
    new_users_per_day_query = db.session.query(func.date(User.created_at), func.count(User.id)).filter(User.created_at >= datetime.utcnow() - timedelta(days=30)).group_by(func.date(User.created_at)).all()
    new_users_per_day = {date.strftime('%Y-%m-%d'): count for date, count in new_users_per_day_query}
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

if __name__ == '__main__':
    with app.app_context():
        # Since the user said they dropped the tables, we will always recreate and seed.
        # For production, you'd want a more robust migration system.
        print("Dropping all tables and recreating them...")
        db.drop_all()
        db.create_all()
        print("Populating database with fresh dummy data...")
        populate_data()
        print("Database populated.")
    app.run(debug=True)
