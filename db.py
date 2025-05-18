from app import *

# create the database tables
with app.app_context():
    db.create_all()


with app.app_context():
    data = [
        User(user_name="admin", password="admin", isAdmin=1),
        User(user_name="shivam", password="shivam"),

        # Demo Data 
        Venue(name="IIT Madras", place="Chennai", capacity=5),
        Venue(name="Nehru Palace", place="Delhi", capacity=10),
        Venue(name="IT TechHub", place="Bangalore", capacity=100),
        Event(name="Laugh Riot", tags="Comedy", timing="Evening", date="2025-06-01", venue_id=1, rating=4),
        Event(name="CodeFest", tags="Coding", timing="Morning", date="2025-06-02", venue_id=2, rating=5),
        Event(name="Melody Night", tags="Music", timing="Night", date="2025-06-03", venue_id=3, rating=4),


        Booking(user_id=2, event_id=1)
    ]
    db.session.add_all(data)
    db.session.commit()

