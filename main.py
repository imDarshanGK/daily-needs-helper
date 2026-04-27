from datetime import datetime
from typing import Literal, Optional
import hashlib
import hmac
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker


DATABASE_URL = "sqlite:///./community_help_hub.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="Daily Needs Helper")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected_digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    actual_digest = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual_digest, expected_digest)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SessionToken(Base):
    __tablename__ = "session_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    city = Column(String(100), nullable=False)
    contact = Column(String(100), nullable=False)
    status = Column(String(20), default="open", nullable=False)
    is_removed = Column(Boolean, default=False, nullable=False)
    created_by = Column(Integer, nullable=False, index=True)
    created_by_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PostRating(Base):
    __tablename__ = "post_ratings"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    rated_user_id = Column(Integer, nullable=False, index=True)
    rated_by_user_id = Column(Integer, nullable=False, index=True)
    score = Column(Integer, nullable=False)
    comment = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PostReport(Base):
    __tablename__ = "post_reports"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    reported_by_user_id = Column(Integer, nullable=False, index=True)
    reason = Column(String(300), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContactRequest(Base):
    __tablename__ = "contact_requests"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    requester_user_id = Column(Integer, nullable=False, index=True)
    owner_user_id = Column(Integer, nullable=False, index=True)
    message = Column(String(300), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def run_schema_migrations() -> None:
    with engine.connect() as connection:
        rating_columns = connection.exec_driver_sql(
            "PRAGMA table_info(post_ratings)"
        ).fetchall()
        if rating_columns:
            column_names = {row[1] for row in rating_columns}
            if "comment" not in column_names:
                connection.exec_driver_sql(
                    "ALTER TABLE post_ratings ADD COLUMN comment VARCHAR(300)"
                )

        posts_columns = connection.exec_driver_sql(
            "PRAGMA table_info(posts)"
        ).fetchall()
        if posts_columns:
            post_column_names = {row[1] for row in posts_columns}
            if "status" not in post_column_names:
                connection.exec_driver_sql(
                    "ALTER TABLE posts ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'open'"
                )
            if "is_removed" not in post_column_names:
                connection.exec_driver_sql(
                    "ALTER TABLE posts ADD COLUMN is_removed BOOLEAN NOT NULL DEFAULT 0"
                )

        connection.exec_driver_sql(
            "UPDATE posts SET status='open' WHERE status IS NULL OR status=''"
        )
        connection.exec_driver_sql(
            "UPDATE posts SET is_removed=0 WHERE is_removed IS NULL"
        )
        admin_count = connection.exec_driver_sql(
            "SELECT COUNT(*) FROM users WHERE is_admin = 1"
        ).scalar()
        if not admin_count:
            first_user_id = connection.exec_driver_sql(
                "SELECT id FROM users ORDER BY id ASC LIMIT 1"
            ).scalar()
            if first_user_id:
                connection.exec_driver_sql(
                    "UPDATE users SET is_admin = 1 WHERE id = ?",
                    (int(first_user_id),),
                )
        connection.commit()


run_schema_migrations()


class SignupInput(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    city: str = Field(min_length=2, max_length=100)


class LoginInput(BaseModel):
    username: str
    password: str


class PostInput(BaseModel):
    title: str = Field(min_length=5, max_length=150)
    description: str = Field(min_length=10, max_length=1000)
    category: str = Field(min_length=2, max_length=50)
    city: str = Field(min_length=2, max_length=100)
    contact: str = Field(min_length=3, max_length=100)


class RatingInput(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default="", max_length=300)


class ReportInput(BaseModel):
    reason: str = Field(min_length=5, max_length=300)


class PostStatusInput(BaseModel):
    status: Literal["open", "resolved"]


class ContactRequestInput(BaseModel):
    message: Optional[str] = Field(default="", max_length=300)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_token_for_user(user_id: int, db: Session) -> str:
    token = f"token-{user_id}-{datetime.utcnow().timestamp()}"
    db_token = SessionToken(token=token, user_id=user_id)
    db.add(db_token)
    db.commit()
    return token


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ", 1)[1]
    db_token = db.query(SessionToken).filter(SessionToken.token == token).first()
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid session token")

    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def ensure_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")


def get_optional_user(authorization: Optional[str], db: Session) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    db_token = db.query(SessionToken).filter(SessionToken.token == token).first()
    if not db_token:
        return None
    return db.query(User).filter(User.id == db_token.user_id).first()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
def favicon():
    return RedirectResponse(url="/static/favicon.svg")


@app.post("/api/signup")
def signup(payload: SignupInput, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == payload.username.strip()).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")

    is_first_user = db.query(User).count() == 0
    user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        city=payload.city.strip(),
        is_admin=is_first_user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token_for_user(user.id, db)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "city": user.city,
            "is_admin": user.is_admin,
        },
    }


@app.post("/api/login")
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token_for_user(user.id, db)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "city": user.city,
            "is_admin": user.is_admin,
        },
    }


@app.get("/api/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "city": current_user.city,
        "is_admin": current_user.is_admin,
    }


@app.get("/api/posts")
def list_posts(
    city: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    current_user = get_optional_user(authorization, db)
    query = db.query(Post).filter(Post.is_removed.is_(False))

    if city:
        query = query.filter(Post.city.ilike(f"%{city.strip()}%"))
    if category:
        query = query.filter(Post.category.ilike(f"%{category.strip()}%"))
    if q:
        term = q.strip()
        query = query.filter(
            (Post.title.ilike(f"%{term}%")) | (Post.description.ilike(f"%{term}%"))
        )

    posts = query.order_by(Post.created_at.desc()).all()
    post_ids = [p.id for p in posts]
    trust_by_post = {}
    approved_requests = set()
    pending_requests = set()

    if current_user and post_ids:
        rows = (
            db.query(ContactRequest.post_id, ContactRequest.status)
            .filter(
                ContactRequest.post_id.in_(post_ids),
                ContactRequest.requester_user_id == current_user.id,
            )
            .all()
        )
        for post_id, status in rows:
            if status == "approved":
                approved_requests.add(int(post_id))
            elif status == "pending":
                pending_requests.add(int(post_id))

    if post_ids:
        rating_rows = (
            db.query(
                PostRating.post_id,
                func.avg(PostRating.score).label("avg_score"),
                func.count(PostRating.id).label("count_score"),
            )
            .filter(PostRating.post_id.in_(post_ids))
            .group_by(PostRating.post_id)
            .all()
        )
        trust_by_post = {
            row.post_id: {
                "avg_rating": round(float(row.avg_score), 2),
                "rating_count": int(row.count_score),
            }
            for row in rating_rows
        }

    return {
        "items": [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "category": p.category,
                "city": p.city,
                "contact": p.contact
                if (
                    current_user
                    and (
                        current_user.id == p.created_by
                        or p.id in approved_requests
                        or current_user.is_admin
                    )
                )
                else None,
                "contact_preview": p.contact[:2] + "******",
                "can_view_contact": bool(
                    current_user
                    and (
                        current_user.id == p.created_by
                        or p.id in approved_requests
                        or current_user.is_admin
                    )
                ),
                "contact_request_status": "approved"
                if p.id in approved_requests
                else ("pending" if p.id in pending_requests else "none"),
                "status": p.status,
                "created_by": p.created_by,
                "created_by_name": p.created_by_name,
                "created_at": p.created_at.isoformat(),
                "avg_rating": trust_by_post.get(p.id, {}).get("avg_rating", 0.0),
                "rating_count": trust_by_post.get(p.id, {}).get("rating_count", 0),
            }
            for p in posts
        ]
    }


@app.get("/api/trusted-helpers")
def list_trusted_helpers(
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    rated_rows = (
        db.query(
            PostRating.rated_user_id.label("user_id"),
            func.avg(PostRating.score).label("avg_score"),
            func.count(PostRating.id).label("rating_count"),
        )
        .group_by(PostRating.rated_user_id)
        .order_by(func.avg(PostRating.score).desc(), func.count(PostRating.id).desc())
        .limit(limit)
        .all()
    )

    if not rated_rows:
        return {"items": []}

    user_ids = [int(row.user_id) for row in rated_rows]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    users_by_id = {u.id: u for u in users}

    post_rows = (
        db.query(Post.created_by, func.count(Post.id).label("post_count"))
        .filter(Post.created_by.in_(user_ids))
        .group_by(Post.created_by)
        .all()
    )
    post_count_by_user = {int(row[0]): int(row[1]) for row in post_rows}

    return {
        "items": [
            {
                "user_id": int(row.user_id),
                "username": users_by_id.get(int(row.user_id)).username
                if users_by_id.get(int(row.user_id))
                else "Unknown",
                "city": users_by_id.get(int(row.user_id)).city
                if users_by_id.get(int(row.user_id))
                else "N/A",
                "avg_rating": round(float(row.avg_score or 0), 2),
                "rating_count": int(row.rating_count or 0),
                "post_count": post_count_by_user.get(int(row.user_id), 0),
            }
            for row in rated_rows
        ]
    }


@app.post("/api/posts")
def create_post(
    payload: PostInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = Post(
        title=payload.title.strip(),
        description=payload.description.strip(),
        category=payload.category.strip(),
        city=payload.city.strip(),
        contact=payload.contact.strip(),
        created_by=current_user.id,
        created_by_name=current_user.username,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": post.id, "message": "Post created"}


@app.post("/api/posts/{post_id}/contact-request")
def create_contact_request(
    post_id: int,
    payload: ContactRequestInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id, Post.is_removed.is_(False)).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.created_by == current_user.id:
        raise HTTPException(status_code=400, detail="You already own this post")

    existing = (
        db.query(ContactRequest)
        .filter(
            ContactRequest.post_id == post_id,
            ContactRequest.requester_user_id == current_user.id,
            ContactRequest.status.in_(["pending", "approved"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Contact request already exists")

    request = ContactRequest(
        post_id=post_id,
        requester_user_id=current_user.id,
        owner_user_id=post.created_by,
        message=(payload.message or "").strip(),
        status="pending",
    )
    db.add(request)
    db.commit()
    return {"message": "Contact request sent"}


@app.get("/api/contact-requests")
def list_contact_requests(
    role: Literal["inbox", "sent"] = Query(default="inbox"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ContactRequest)
    if role == "inbox":
        query = query.filter(ContactRequest.owner_user_id == current_user.id)
    else:
        query = query.filter(ContactRequest.requester_user_id == current_user.id)

    rows = query.order_by(ContactRequest.created_at.desc()).all()
    post_ids = [r.post_id for r in rows]
    user_ids = [r.requester_user_id for r in rows] + [r.owner_user_id for r in rows]
    posts = db.query(Post).filter(Post.id.in_(post_ids)).all() if post_ids else []
    users = db.query(User).filter(User.id.in_(set(user_ids))).all() if user_ids else []
    posts_by_id = {p.id: p for p in posts}
    users_by_id = {u.id: u for u in users}

    return {
        "items": [
            {
                "id": r.id,
                "post_id": r.post_id,
                "post_title": posts_by_id.get(r.post_id).title
                if posts_by_id.get(r.post_id)
                else "Unknown",
                "status": r.status,
                "message": r.message or "",
                "requester_name": users_by_id.get(r.requester_user_id).username
                if users_by_id.get(r.requester_user_id)
                else "Unknown",
                "owner_name": users_by_id.get(r.owner_user_id).username
                if users_by_id.get(r.owner_user_id)
                else "Unknown",
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


@app.post("/api/contact-requests/{request_id}/approve")
def approve_contact_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = db.query(ContactRequest).filter(ContactRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.owner_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed")
    req.status = "approved"
    db.commit()
    return {"message": "Request approved"}


@app.post("/api/contact-requests/{request_id}/reject")
def reject_contact_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = db.query(ContactRequest).filter(ContactRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.owner_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed")
    req.status = "rejected"
    db.commit()
    return {"message": "Request rejected"}


@app.patch("/api/posts/{post_id}/status")
def update_post_status(
    post_id: int,
    payload: PostStatusInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.is_removed:
        raise HTTPException(status_code=400, detail="Post has been removed")

    if post.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed")

    post.status = payload.status
    db.commit()
    return {"message": f"Post marked as {payload.status}"}


@app.delete("/api/posts/{post_id}")
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed")

    post.is_removed = True
    db.commit()
    return {"message": "Post removed"}


@app.post("/api/posts/{post_id}/report")
def report_post(
    post_id: int,
    payload: ReportInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id, Post.is_removed.is_(False)).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.created_by == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot report your own post")

    already_reported = (
        db.query(PostReport)
        .filter(
            PostReport.post_id == post_id,
            PostReport.reported_by_user_id == current_user.id,
        )
        .first()
    )
    if already_reported:
        raise HTTPException(status_code=400, detail="You already reported this post")

    report = PostReport(
        post_id=post_id,
        reported_by_user_id=current_user.id,
        reason=payload.reason.strip(),
    )
    db.add(report)
    db.commit()
    return {"message": "Post reported"}


@app.get("/api/admin/posts")
def list_admin_posts(
    include_removed: bool = Query(default=True),
    only_reported: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin(current_user)

    posts_query = db.query(Post)
    if not include_removed:
        posts_query = posts_query.filter(Post.is_removed.is_(False))
    if only_reported:
        reported_ids = db.query(PostReport.post_id).distinct().all()
        reported_ids = [row[0] for row in reported_ids]
        if not reported_ids:
            return {"items": []}
        posts_query = posts_query.filter(Post.id.in_(reported_ids))

    posts = posts_query.order_by(Post.created_at.desc()).all()
    post_ids = [p.id for p in posts]
    report_counts = {}
    if post_ids:
        rows = (
            db.query(PostReport.post_id, func.count(PostReport.id))
            .filter(PostReport.post_id.in_(post_ids))
            .group_by(PostReport.post_id)
            .all()
        )
        report_counts = {int(post_id): int(count) for post_id, count in rows}

    return {
        "items": [
            {
                "id": p.id,
                "title": p.title,
                "city": p.city,
                "status": p.status,
                "is_removed": p.is_removed,
                "created_by_name": p.created_by_name,
                "report_count": report_counts.get(p.id, 0),
                "created_at": p.created_at.isoformat(),
            }
            for p in posts
        ]
    }


@app.post("/api/admin/posts/{post_id}/remove")
def admin_remove_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin(current_user)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.is_removed = True
    db.commit()
    return {"message": "Post removed by admin"}


@app.post("/api/admin/posts/{post_id}/restore")
def admin_restore_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin(current_user)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.is_removed = False
    db.commit()
    return {"message": "Post restored by admin"}


@app.post("/api/posts/{post_id}/rate")
def rate_post(
    post_id: int,
    payload: RatingInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.created_by == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot rate your own post")

    existing = (
        db.query(PostRating)
        .filter(
            PostRating.post_id == post_id,
            PostRating.rated_by_user_id == current_user.id,
        )
        .first()
    )

    if existing:
        existing.score = payload.score
        existing.comment = (payload.comment or "").strip()
        existing.created_at = datetime.utcnow()
    else:
        rating = PostRating(
            post_id=post_id,
            rated_user_id=post.created_by,
            rated_by_user_id=current_user.id,
            score=payload.score,
            comment=(payload.comment or "").strip(),
        )
        db.add(rating)

    db.commit()

    trust = (
        db.query(
            func.avg(PostRating.score).label("avg_score"),
            func.count(PostRating.id).label("count_score"),
        )
        .filter(PostRating.post_id == post_id)
        .first()
    )

    return {
        "message": "Rating submitted",
        "avg_rating": round(float(trust.avg_score or 0), 2),
        "rating_count": int(trust.count_score or 0),
    }
