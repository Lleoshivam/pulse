
from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'MAD_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Flask Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Models


class Venue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    place = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    events = db.relationship('Event', backref='venue',
                             lazy=True, cascade='delete')


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    tags = db.Column(db.String(20), nullable=False)
    timing = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, default=200)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    isAdmin = db.Column(db.Integer)


class Booking(db.Model):
    booking_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.id'),  nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)


def get_total_booked_tickets(venueid, date, event):
    total_quantity = db.session.query(func.sum(Booking.quantity)).join(Event).filter(
        Event.venue_id == venueid, Event.date == date, Event.name == event).scalar()
    return total_quantity or 0


# Routes


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    session.pop('user_logged_in', None)
    logout_user()
    return render_template('index.html')


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        name = request.form['user_name']
        password = request.form['password']
        user = User.query.filter_by(user_name=name).first()
        if user and password == "admin" and user.isAdmin == 1:
            if 'user_logged_in' in session:
                error = "You are logged from user account, Logout User account first to login in admin "
                return render_template('admin_login.html', error=error)
            else:
                session['logged_in'] = True
                login_user(user)
                return redirect(url_for('admin'))
        else:
            error = "Enter Correct Credentials"
            return render_template('admin_login.html', error=error)
    return render_template('admin_login.html')


@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        name = request.form['user_name']
        password = request.form['password']
        user = User.query.filter_by(user_name=name).first()
        if user and password == user.password:
            if user.isAdmin == 1:
                error = "You are entering admin credentials in user login"
                return render_template('user_login.html', error=error)
            else:
                if 'logged_in' in session:
                    error = "You are logged from Admin account, Logout Admin account first to login in User Account "
                    return render_template('user_login.html', error=error)
                else:
                    session['user_logged_in'] = True
                    session['user_id'] = user.id
                    login_user(user)
                    return redirect(url_for('user_dash', name=name))
        else:
            error = "Invalid Username or Password"
            return render_template('user_login.html', error=error)
    return render_template('user_login.html')


@app.route('/history', methods=['GET'])
@login_required
def history():

    # Retrieve the bookings of the logged-in user from the database
    user_bookings = Booking.query.filter_by(user_id=session['user_id']).all()

    # Create a list of dictionaries containing the booking information
    booking_info = []
    for booking in user_bookings:
        event = Event.query.join(Booking).filter(
            Booking.booking_id == booking.booking_id).first()
        if event:
            quantity = booking.quantity
            total_price = quantity * event.price
            booking_info.append({
                'id': booking.booking_id,
                'event_name': event.name,
                'event_date': event.date,
                'venue_name': event.venue.name,
                'place': event.venue.place,
                'price': event.price,
                'booking_date': booking.booking_date,
                'quantity': quantity,
                'total_price': total_price
            })

    return render_template('history.html', booking_info=booking_info)


@app.route('/user_dash')
def user_dash():
    venues = Venue.query.all()
    events = Event.query.all()
    if session.get('user_logged_in'):
        return render_template('user_dash.html', events=events, venues=venues)
    else:
        return redirect(url_for('user_login', error='Login first to access the account'))


# @app.route('/user_dash')
# def search_event():
#     venues = Venue.query.all()
#     events = Event.query.all()
#     return render_template('user_dash.html')


@app.route('/user')
@login_required
def user():
    venues = Venue.query.all()
    events = Event.query.all()
    return render_template('user.html', events=events, venues=venues)


@app.route('/user/search', methods=['POST'])
@login_required
def search():
    venues = Venue.query.all()
    events = Event.query.all()
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login', error='Login first to access the account'))

    if request.method == 'POST':
        date = request.form.get('date')
        tags = request.form.get('tags')
        if tags:
            tags = request.form.get('tags').capitalize()
        venue_id = request.form.get('venue')
        selected_events = []

        for event in events:
            if venue_id == str(event.venue_id):
                selected_events.append(event)

        for event in events:
            if tags == event.tags:
                selected_events.append(event)

        return render_template('user.html', venues=venues, events=selected_events,  date=date, tags=tags)
    return render_template('user.html', venues=venues, events=selected_events)


@app.route('/book/<int:id>', methods=['GET', 'POST'])
@login_required
def book(id):
    event = Event.query.get_or_404(id)
    venues = Venue.query.all()
    if request.method == 'POST':
        quantity = int(request.form['quantity'])
        user_id = session.get('user_id')
        total_booked_tickets = get_total_booked_tickets(
            event.venue_id, event.date, event.name)
        remaining_seats = event.venue.capacity - total_booked_tickets
        if remaining_seats <= 0:

            return redirect(url_for('user', id=id, msg="Sorry, all seats are booked. The Show is Housefull, Please choose another event."))
        elif quantity > remaining_seats:
            msg = f"Sorry, only {remaining_seats} seats are available for this event. Please choose a lower quantity."

            return redirect(url_for('book', id=id, msg=msg))
        else:
            ticket = Booking(event_id=id, user_id=user_id, quantity=quantity)
            db.session.add(ticket)
            db.session.commit()
            msg = f'Ticket booked successfully! You have booked {quantity} tickets for {event.name} on {event.date}.'
            return redirect(url_for('user', msg=msg))
    return render_template('book.html', event=event, venue=venues)


@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        name = request.form['user_name']
        password = request.form['password']
        re_password = request.form['re_password']
        user = User.query.filter_by(user_name=name).first()
        if user:
            error = "User Name exists, try any other User Name"
            return render_template('register.html', error=error)
        elif password != re_password:
            error = "Both the passwords, did not matched"
            return render_template('register.html', error=error)
        elif len(password) < 4:
            error = "Password length should be 5 or more than 5"
            return render_template('register.html', error=error)
        else:
            u = User(user_name=name, password=password)
            db.session.add(u)
            db.session.commit()
            return redirect(url_for('user_login'))
    return render_template('register.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/admin')
def admin():
    venues = Venue.query.all()
    events = Event.query.all()
    if session.get('logged_in'):
        return render_template('admin.html', venues=venues, events=events, get_total_booked_tickets=get_total_booked_tickets)
    else:
        return redirect(url_for('admin_login', error='Login first to access the account'))


@app.route('/add_venue', methods=['GET', 'POST'])
@login_required
def add_venue():
    if current_user.isAdmin != 1:
        error = " You dont have permission, Login as Admin"
        return render_template('admin_login.html', error=error)

    if request.method == 'POST':

        name = request.form['name']
        place = request.form['place']
        capacity = request.form['capacity']
        venue = Venue(name=name, place=place, capacity=capacity)
        db.session.add(venue)
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('add_venue.html')


@app.route('/edit_venue/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_venue(id):
    if current_user.isAdmin != 1:
        error = " You dont have permission, Login as Admin"
        return render_template('admin_login.html', error=error)

    venue = Venue.query.get_or_404(id)
    if request.method == 'POST':
        venue.name = request.form['name']
        venue.place = request.form['place']

        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_venue.html', venue=venue)


@app.route('/delete_venue/<int:id>', methods=['POST'])
@login_required
def delete_venue(id):
    if current_user.isAdmin != 1:
        error = " You dont have permission, Login as Admin"
        return render_template('admin_login.html', error=error)

    venue = Venue.query.get_or_404(id)
    db.session.delete(venue)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
    if current_user.isAdmin != 1:
        error = " You dont have permission, Login as Admin"
        return render_template('admin_login.html', error=error)
    venues = Venue.query.all()
    if request.method == 'POST':
        name = request.form['name']
        rating = request.form['rating']
        tags = request.form['tags']
        timing = request.form['timing']
        date = request.form['date']
        venues_checked = request.form.getlist('venues')
        for venue_id in venues_checked:
            event = Event(name=name, rating=rating, tags=tags,
                          timing=timing, venue_id=venue_id, date=date)
            db.session.add(event)
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('add_event.html', venues=venues)

@app.route('/add_event_byUser', methods=['GET', 'POST'])
@login_required
def add_event_byUser():

    venues = Venue.query.all()
    if request.method == 'POST':
        name = request.form['name']
        rating = request.form['rating']
        tags = request.form['tags']
        timing = request.form['timing']
        date = request.form['date']
        venues_checked = request.form.getlist('venues')
        for venue_id in venues_checked:
            event = Event(name=name, rating=rating, tags=tags,
                          timing=timing, venue_id=venue_id, date=date)
            db.session.add(event)
        db.session.commit()
        return redirect(url_for('user_dash'))
    return render_template('add_event_byUser.html', venues=venues)

@app.route('/edit_event/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_event(id):
    if current_user.isAdmin != 1:
        error = " You dont have permission, Login as Admin"
        return render_template('admin_login.html', error=error)
    event = Event.query.get_or_404(id)
    venues = Venue.query.all()
    if request.method == 'POST':
        event.name = request.form['name']
        event.rating = request.form['rating']
        event.tags = request.form['tags']
        event.timing = request.form['timing']
        event.venue_id = request.form['venue']
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_event.html', event=event, venues=venues)


@app.route('/edit_event_ratingtags/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_event_ratingtags(id):
    if current_user.isAdmin != 1:
        error = " You dont have permission, Login as Admin"
        return render_template('admin_login.html', error=error)
    event = Event.query.get_or_404(id)
    event_with_same_name = Event.query.filter_by(name=event.name).all()
    if request.method == 'POST':
        new_rating = int(request.form['rating'])
        new_tags = request.form['tags']
        for m in event_with_same_name:
            if m.id != event.id:
                m.rating = new_rating
                m.tags = new_tags

        event.rating = new_rating
        event.tags = new_tags
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_event_ratingtags.html', event=event)


@app.route('/delete_event/<int:id>', methods=['POST'])
@login_required
def delete_event(id):
    if current_user.isAdmin != 1:
        error = " You dont have permission, Login as Admin"
        return render_template('admin_login.html', error=error)
    event = Event.query.get_or_404(id)
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug="True")
