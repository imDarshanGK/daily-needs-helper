from datetime import datetime
from typing import Optional
import hashlib
import hmac
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
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


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/signup")
def signup(payload: SignupInput, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == payload.username.strip()).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        city=payload.city.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token_for_user(user.id, db)
    return {
        "token": token,
        "user": {"id": user.id, "username": user.username, "city": user.city},
    }


@app.post("/api/login")
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token_for_user(user.id, db)
    return {
        "token": token,
        "user": {"id": user.id, "username": user.username, "city": user.city},
    }


@app.get("/api/posts")
def list_posts(
    city: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Post)

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
                "contact": p.contact,
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

    db.delete(post)
    db.commit()
    return {"message": "Post deleted"}


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
