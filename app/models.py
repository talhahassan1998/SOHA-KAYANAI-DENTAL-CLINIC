"""SQLAlchemy models for the dental clinic application."""
from datetime import datetime, date

from app.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Doctor(db.Model, TimestampMixin):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    specialty = db.Column(db.String(160), nullable=False)
    credentials = db.Column(db.String(160))
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(500))
    years_experience = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=True, index=True)
    display_order = db.Column(db.Integer, default=0)

    appointments = db.relationship("Appointment", back_populates="doctor")

    def __repr__(self):
        return f"<Doctor {self.name}>"


class Service(db.Model, TimestampMixin):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    short_description = db.Column(db.String(300))
    full_description = db.Column(db.Text)
    icon_name = db.Column(db.String(60), default="tooth")
    image_url = db.Column(db.String(500))
    is_featured = db.Column(db.Boolean, default=True, index=True)
    display_order = db.Column(db.Integer, default=0)

    appointments = db.relationship("Appointment", back_populates="service")

    def __repr__(self):
        return f"<Service {self.name}>"


class AppointmentStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

    CHOICES = [PENDING, CONFIRMED, CANCELLED]


class Gender:
    """Stored as short constants rather than a native enum, matching AppointmentStatus.

    The column is nullable because appointments booked before this field existed have no
    value; new bookings are required to pick one (enforced in the form and the API).
    """

    FEMALE = "female"
    MALE = "male"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

    CHOICES = [FEMALE, MALE, OTHER, PREFER_NOT_TO_SAY]

    LABELS = {
        FEMALE: "Female",
        MALE: "Male",
        OTHER: "Other",
        PREFER_NOT_TO_SAY: "Prefer not to say",
    }

    @classmethod
    def label(cls, value):
        return cls.LABELS.get(value, "Not specified")


class Appointment(db.Model, TimestampMixin):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(40), nullable=False)
    gender = db.Column(db.String(20))

    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=True)

    preferred_date = db.Column(db.Date, nullable=False, index=True)
    preferred_time = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)

    status = db.Column(db.String(20), default=AppointmentStatus.PENDING, index=True)

    service = db.relationship("Service", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")

    def __repr__(self):
        return f"<Appointment {self.full_name} on {self.preferred_date}>"


class Testimonial(db.Model, TimestampMixin):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(160), nullable=False)
    patient_photo_url = db.Column(db.String(500))
    rating = db.Column(db.Integer, default=5)
    quote = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.String(160))
    is_featured = db.Column(db.Boolean, default=True, index=True)
    display_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Testimonial {self.patient_name}>"


class BlogPost(db.Model, TimestampMixin):
    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    excerpt = db.Column(db.String(400))
    content = db.Column(db.Text, nullable=False)
    cover_image_url = db.Column(db.String(500))
    author = db.Column(db.String(120), default="Clinic Team")
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True, index=True)

    def __repr__(self):
        return f"<BlogPost {self.title}>"


class GalleryImage(db.Model, TimestampMixin):
    __tablename__ = "gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(60), default="before-after", index=True)
    before_image_url = db.Column(db.String(500))
    after_image_url = db.Column(db.String(500))
    caption = db.Column(db.String(300))
    display_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<GalleryImage {self.title}>"


class FAQ(db.Model, TimestampMixin):
    __tablename__ = "faqs"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), default="General")
    display_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<FAQ {self.question[:40]}>"


class ContactMessage(db.Model, TimestampMixin):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(40))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, index=True)

    def __repr__(self):
        return f"<ContactMessage {self.name}>"


class NewsletterSubscriber(db.Model):
    __tablename__ = "newsletter_subscribers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<NewsletterSubscriber {self.email}>"
