"""Idempotent sample data seeder for the dental clinic database.

Run with `flask seed` (registered as a CLI command) or `python seed.py`.
"""
from datetime import datetime, timedelta

from app.extensions import db
from app.models import (
    Doctor, Service, Testimonial, BlogPost, GalleryImage, FAQ,
)

# NOTE: these are stock portraits of models, standing in for named real clinicians.
# Replace each with the actual staff member's photo before this site goes live — a
# stock face shown under a real doctor's name and credentials misrepresents both the
# model and the clinic. Drop a 4:5 photo into app/static/images/ and update photo_url.
# Kept for any doctor added later who doesn't have a photo yet.
DOCTOR_PHOTO_PLACEHOLDER = "/static/images/doctor-placeholder.svg"

DOCTORS = [
    dict(
        name="Dr. Soha Kayani", slug="soha-kayani", specialty="Implant & Restorative Dentistry",
        credentials="BDS, RDS, MSc Implantology", years_experience=16, display_order=1,
        bio="Dr. Kayani is the founder of the clinic and has placed over 4,000 implants, specializing in full-arch restorations using guided digital planning.",
        photo_url="/static/images/dr-soha-kayani.jpg",
    ),
    dict(
        name="Dr. Ayesha Farooq", slug="ayesha-farooq", specialty="Cosmetic Dentistry & Veneers",
        credentials="BDS, RDS, FCPS Prosthodontics", years_experience=12, display_order=2,
        bio="Dr. Farooq designs smile makeovers combining porcelain veneers, whitening and digital smile previews.",
        photo_url="/static/images/dr-ayesha-farooq.jpg",
    ),
    dict(
        name="Dr. Bilal Ahmed", slug="bilal-ahmed", specialty="Braces & Clear Aligners",
        credentials="BDS, RDS, MDS Orthodontics", years_experience=11, display_order=3,
        bio="Dr. Ahmed treats complex bite corrections with both traditional braces and Invisalign clear aligners.",
        photo_url="/static/images/dr-bilal-ahmed.jpg",
    ),
    dict(
        name="Dr. Mahnoor Raza", slug="mahnoor-raza", specialty="Pediatric & Preventive Care",
        credentials="BDS, RDS, Cert. Pediatric Dentistry", years_experience=10, display_order=4,
        bio="Dr. Raza creates calm, friendly first experiences for young patients, with a focus on prevention.",
        photo_url="/static/images/dr-mahnoor-raza.jpg",
    ),
]

SERVICES = [
    dict(name="Dental Implants", slug="dental-implants", icon_name="implant", display_order=1,
         short_description="Permanent titanium roots that restore missing teeth with lifelong strength.",
         full_description="Our guided 3D implant planning delivers precise, minimally invasive placement with fast healing and a lifetime-focused restoration protocol.",
         image_url="/static/images/svc-dental-implants.jpg"),
    dict(name="Teeth Whitening", slug="teeth-whitening", icon_name="whitening", display_order=2,
         short_description="Clinically supervised whitening that brightens up to 8 shades in one visit.",
         full_description="Low-sensitivity, high-concentration whitening gel activated under LED light for dramatic same-day results with minimal enamel sensitivity.",
         image_url="/static/images/teeth-whitening.jpg"),
    dict(name="Root Canal Treatment", slug="root-canal-treatment", icon_name="root-canal", display_order=3,
         short_description="Microscope-assisted endodontics that save teeth pain-free.",
         full_description="Rotary instrumentation with microscope visualization means faster treatment with far greater comfort than traditional root canal therapy.",
         image_url="/static/images/svc-root-canal.jpg"),
    dict(name="Orthodontics", slug="orthodontics", icon_name="braces", display_order=4,
         short_description="Clean clear aligners and modern braces for beautifully aligned smiles.",
         full_description="Digital scanning, treatment simulation and remote progress monitoring keep your orthodontic journey efficient and transparent.",
         image_url="/static/images/svc-orthodontics.jpg"),
    dict(name="Invisalign", slug="invisalign", icon_name="invisalign", display_order=5,
         short_description="Nearly invisible aligners that straighten teeth without brackets or wires.",
         full_description="Custom 3D-printed aligner sequences move teeth gradually and comfortably, with progress tracked via digital scans every few weeks.",
         image_url="/static/images/svc-invisalign.jpg"),
    dict(name="Veneers", slug="veneers", icon_name="veneers", display_order=6,
         short_description="Ultra-thin porcelain shells that perfect shape, color and symmetry.",
         full_description="Minimal-prep veneers crafted by master ceramists give a natural, long-lasting finish tailored to your facial proportions.",
         image_url="/static/images/svc-veneers.jpg"),
    dict(name="Smile Makeover", slug="smile-makeover", icon_name="smile", display_order=7,
         short_description="A full design blueprint tailored to your facial proportions and desires.",
         full_description="Digital smile previews combine whitening, veneers and gum contouring into one coordinated makeover plan you approve before we begin.",
         image_url="/static/images/svc-smile-makeover.jpg"),
    dict(name="Cosmetic Dentistry", slug="cosmetic-dentistry", icon_name="cosmetic", display_order=8,
         short_description="Bonding, contouring and color correction for a refined natural look.",
         full_description="From subtle chip repairs to full aesthetic reconstructions, our cosmetic menu is built around conservative, tooth-preserving techniques.",
         image_url="/static/images/svc-cosmetic-dentistry.jpg"),
    dict(name="Pediatric Dentistry", slug="pediatric-dentistry", icon_name="pediatric", display_order=9,
         short_description="Gentle, playful care for kids that builds lifelong healthy habits.",
         full_description="Preventive sealants, fluoride therapy and friendly clinicians help children build positive associations with dental visits early on.",
         image_url="/static/images/svc-pediatric.jpg"),
    dict(name="Tooth Extraction", slug="tooth-extraction", icon_name="extraction", display_order=10,
         short_description="Safe, surgical and simple extractions with rapid, comfortable healing.",
         full_description="Including wisdom tooth removal, our extractions use modern sedation options and guided socket preservation for smoother recovery.",
         image_url="/static/images/svc-extraction.jpg"),
    dict(name="Emergency Dental Care", slug="emergency-dental-care", icon_name="emergency", display_order=11,
         short_description="Same-day emergency slots reserved daily, plus 24/7 on-call dentist.",
         full_description="Severe pain, trauma or a knocked-out tooth — our team prioritizes emergency cases with same-day appointments and after-hours support.",
         image_url="/static/images/svc-emergency.jpg"),
]

TESTIMONIALS = [
    dict(patient_name="Sana Malik", treatment="Porcelain Veneers", rating=5, display_order=1,
         quote="I finally smile in photos. The digital preview meant I knew exactly what I was getting before we started.",
         patient_photo_url="/static/images/patient-sana.jpg"),
    dict(patient_name="Usman Tariq", treatment="Dental Implants", rating=5, display_order=2,
         quote="Two implants, zero pain, and the team called me the next morning to check in. Genuinely exceptional care.",
         patient_photo_url="/static/images/patient-usman.jpg"),
    dict(patient_name="Hira Sheikh", treatment="Clear Aligners", rating=5, display_order=3,
         quote="Fourteen months of aligners and my bite feels completely different. Dr. Ahmed explained every stage clearly.",
         patient_photo_url="/static/images/patient-hira.jpg"),
    dict(patient_name="Fahad Chaudhry", treatment="Root Canal Treatment", rating=5, display_order=4,
         quote="I was dreading this for months. It was over in under an hour and I felt almost nothing.",
         patient_photo_url="/static/images/patient-fahad.jpg"),
    dict(patient_name="Zara Iqbal", treatment="Smile Makeover", rating=5, display_order=5,
         quote="From consultation to final reveal, everything was mapped out. Worth every visit.",
         patient_photo_url="/static/images/patient-zara.jpg"),
    dict(patient_name="Hamza Qureshi", treatment="Emergency Dental Care", rating=5, display_order=6,
         quote="Chipped a tooth on a Saturday and they saw me within two hours. Incredible responsiveness.",
         patient_photo_url="/static/images/patient-hamza.jpg"),
]

# Each entry uses its own distinct clinical scene — the previous set repeated the same
# lipstick smile close-up three times and two empty grey rooms, which read as filler.
GALLERY_IMAGES = [
    dict(title="Porcelain veneers", category="before-after", display_order=1, caption="8 upper porcelain veneers · 2 visits",
         before_image_url="/static/images/gal-veneers.jpg",
         after_image_url="/static/images/gal-veneers.jpg"),
    dict(title="Full-arch implants", category="before-after", display_order=2, caption="Fixed bridge on 6 implants",
         before_image_url="/static/images/gal-implants.jpg",
         after_image_url="/static/images/gal-implants.jpg"),
    dict(title="Pediatric sealants", category="facility", display_order=3, caption="Gentle first visit for a 5 year old",
         before_image_url="/static/images/gal-pediatric.jpg",
         after_image_url="/static/images/gal-pediatric.jpg"),
    dict(title="In-clinic whitening", category="before-after", display_order=4, caption="8 shades brighter · 60 minutes",
         before_image_url="/static/images/gal-whitening.jpg",
         after_image_url="/static/images/gal-whitening.jpg"),
    dict(title="Braces & aligners", category="before-after", display_order=5, caption="Bracket adjustment at 6 months",
         before_image_url="/static/images/gal-braces.jpg",
         after_image_url="/static/images/gal-braces.jpg"),
    dict(title="Digital diagnostics", category="facility", display_order=6, caption="3D scan-guided treatment planning",
         before_image_url="/static/images/gal-diagnostics.jpg",
         after_image_url="/static/images/gal-diagnostics.jpg"),
]

BLOG_POSTS = [
    dict(title="5 Habits That Quietly Wreck Your Enamel", slug="habits-that-wreck-enamel", author="Dr. Ayesha Farooq",
         excerpt="Enamel doesn't regenerate — small daily habits determine whether it lasts a lifetime or wears thin by 40.",
         content="Enamel is the hardest substance in the human body, but it is not indestructible. Acidic drinks, aggressive brushing, teeth grinding and even ice-chewing gradually erode it in ways that are irreversible. In this post we cover the five most common offenders we see in clinic, and simple substitutions that protect your enamel without giving up the foods you love. We also explain when enamel erosion becomes a candidate for veneers or bonding versus when a change in routine is enough to stop further damage.",
         cover_image_url="/static/images/blog-enamel.jpg"),
    dict(title="Invisalign vs. Traditional Braces: What Actually Differs", slug="invisalign-vs-braces", author="Dr. Bilal Ahmed",
         excerpt="Both can achieve excellent results — the right choice depends on your bite complexity, lifestyle and timeline.",
         content="Patients often assume Invisalign is simply a more convenient version of braces, but the mechanics differ meaningfully. Clear aligners excel at cosmetic alignment and mild-to-moderate crowding, while traditional braces remain the gold standard for complex bite corrections requiring vertical or rotational movement. This article breaks down treatment timelines, maintenance requirements, and typical cost ranges for both options so you can have an informed conversation at your consultation.",
         cover_image_url="/static/images/blog-invisalign-braces.jpg"),
    dict(title="What to Expect at Your Child's First Dental Visit", slug="childs-first-dental-visit", author="Dr. Mahnoor Raza",
         excerpt="A calm first impression shapes how your child feels about dental care for years. Here's how we prepare families.",
         content="Pediatric dental specialists recommend a first visit by age one, but many parents wait until symptoms appear. Early visits are primarily about comfort and prevention rather than treatment — building trust, checking developmental milestones, and giving parents practical guidance on brushing technique and diet. We walk through exactly what happens during a first appointment at our clinic, and tips for talking to your child beforehand.",
         cover_image_url="/static/images/blog-child-first-visit.jpg"),
]

FAQS = [
    dict(question="Do you offer installment plans for expensive treatments?", category="Billing", display_order=1,
         answer="Yes, we offer easy installment plans for implants, orthodontics and smile makeovers so treatment cost is never a barrier to care. Our front desk can walk you through the options before your visit."),
    dict(question="How often should I get a professional cleaning?", category="General", display_order=2,
         answer="Most patients benefit from a cleaning every six months, though patients with gum disease history may be advised to come in more frequently."),
    dict(question="Is teeth whitening safe for sensitive teeth?", category="Cosmetic", display_order=3,
         answer="We offer low-sensitivity whitening protocols and can apply a desensitizing treatment beforehand for patients with known sensitivity."),
    dict(question="What happens during a dental emergency after hours?", category="Emergency", display_order=4,
         answer="Call our clinic number and you'll be connected to our on-call dentist, who can advise on immediate steps and arrange a same-day or next-morning slot."),
    dict(question="How long does an implant take from start to finish?", category="Implants", display_order=5,
         answer="A typical single implant takes 3 to 6 months from placement to final crown, allowing time for osseointegration. Same-day options exist for select cases."),
    dict(question="Can I switch from braces to Invisalign mid-treatment?", category="Orthodontics", display_order=6,
         answer="In many cases yes. Dr. Ahmed can assess your current progress and determine whether transitioning to aligners is appropriate for your remaining treatment."),
    dict(question="Do you treat dental anxiety or phobia?", category="General", display_order=7,
         answer="Absolutely. We offer sedation options, extended appointment times, and a judgment-free approach for patients who feel anxious about dental visits."),
    dict(question="What age can my child start orthodontic evaluation?", category="Pediatric", display_order=8,
         answer="We recommend a first orthodontic evaluation by age seven, even if treatment isn't needed until later — it helps us catch developing bite issues early."),
]


def run_seed():
    _seed_doctors()
    _seed_services()
    _seed_testimonials()
    _seed_gallery()
    _seed_blog()
    _seed_faqs()
    db.session.commit()


def _seed_doctors():
    for data in DOCTORS:
        if not Doctor.query.filter_by(slug=data["slug"]).first():
            db.session.add(Doctor(**data))


def _seed_services():
    for data in SERVICES:
        if not Service.query.filter_by(slug=data["slug"]).first():
            db.session.add(Service(**data))


def _seed_testimonials():
    if Testimonial.query.count() == 0:
        for data in TESTIMONIALS:
            db.session.add(Testimonial(**data))


def _seed_gallery():
    if GalleryImage.query.count() == 0:
        for data in GALLERY_IMAGES:
            db.session.add(GalleryImage(**data))


def _seed_blog():
    for i, data in enumerate(BLOG_POSTS):
        if not BlogPost.query.filter_by(slug=data["slug"]).first():
            post = BlogPost(published_at=datetime.utcnow() - timedelta(days=(len(BLOG_POSTS) - i) * 7), **data)
            db.session.add(post)


def _seed_faqs():
    if FAQ.query.count() == 0:
        for data in FAQS:
            db.session.add(FAQ(**data))


if __name__ == "__main__":
    from app import create_app

    app = create_app("development")
    with app.app_context():
        run_seed()
        print("Database seeded successfully.")
