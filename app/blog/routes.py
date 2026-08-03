from flask import render_template, request
from sqlalchemy import or_

from app.blog import blog_bp
from app.models import BlogPost


@blog_bp.route("/")
def list_posts():
    q = request.args.get("q", "").strip()
    query = BlogPost.query.filter_by(is_published=True)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(BlogPost.title.ilike(like), BlogPost.content.ilike(like), BlogPost.excerpt.ilike(like))
        )
    posts = query.order_by(BlogPost.published_at.desc()).all()
    return render_template("blog/list.html", posts=posts, query=q)


@blog_bp.route("/<slug>")
def detail(slug):
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    recent = (
        BlogPost.query.filter(BlogPost.id != post.id, BlogPost.is_published.is_(True))
        .order_by(BlogPost.published_at.desc())
        .limit(3)
        .all()
    )
    return render_template("blog/detail.html", post=post, recent=recent)
