import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Security, Query

from fastapi.security import APIKeyHeader

from sqlalchemy import func

from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app import models, schemas, ai_service

# Modern lifespan event handler to initialize database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="News Content Management API",
    description="A backend system for managing news posts for a social media page, featuring Groq AI summarization.",
    version="1.0.0",
    lifespan=lifespan
)

# API Key Security Dependency
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    # Use environment variable API_KEY (default: "secret-api-key")
    expected_key = os.getenv("API_KEY", "secret-api-key")
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key. Use the 'X-API-Key' header."
        )
    return api_key


# Helper function to check duplicate titles
def check_duplicate_title(db: Session, title: str, exclude_id: Optional[int] = None) -> None:
    query = db.query(models.Post).filter(models.Post.title == title)
    if exclude_id is not None:
        query = query.filter(models.Post.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A post with this title already exists."
        )


# 1. POST /posts - Create a post
@app.post("/posts", response_model=schemas.PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: schemas.PostCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    # Prevent duplicate titles
    check_duplicate_title(db, post_in.title)
    
    db_post = models.Post(
        title=post_in.title,
        content=post_in.content,
        category=post_in.category,
        status=post_in.status.value
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


# 2. GET /posts - List all posts with filtering, sorting and pagination
@app.get("/posts", response_model=List[schemas.PostResponse])
def get_posts(
    category: Optional[str] = Query(None, description="Filter by category"),
    status_filter: Optional[schemas.PostStatus] = Query(None, alias="status", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title and content"),
    sort_by: str = Query("created_at", regex="^(created_at|views)$", description="Sort by field"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sorting order"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
    db: Session = Depends(get_db)
):
    query = db.query(models.Post)
    
    # Apply category filter
    if category:
        query = query.filter(models.Post.category == category)
        
    # Apply status filter
    if status_filter:
        query = query.filter(models.Post.status == status_filter.value)
        
    # Apply search filter (checks title and content, case-insensitive)
    if search:
        query = query.filter(
            (models.Post.title.ilike(f"%{search}%")) |
            (models.Post.content.ilike(f"%{search}%"))
        )
        
    # Apply sorting
    sort_col = getattr(models.Post, sort_by)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())
        
    # Apply pagination
    return query.offset(skip).limit(limit).all()


# 3. GET /posts/{post_id} - Retrieve a single post
@app.get("/posts/{post_id}", response_model=schemas.PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found."
        )
    return db_post


# 4. PUT /posts/{post_id} - Complete update
@app.put("/posts/{post_id}", response_model=schemas.PostResponse)
def update_post(
    post_id: int,
    post_in: schemas.PostUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found."
        )
        
    # Prevent duplicate titles (excluding the current post)
    check_duplicate_title(db, post_in.title, exclude_id=post_id)
    
    db_post.title = post_in.title
    db_post.content = post_in.content
    db_post.category = post_in.category
    db_post.status = post_in.status.value
    
    db.commit()
    db.refresh(db_post)
    return db_post


# Bonus: PATCH /posts/{post_id} - Partial update
@app.patch("/posts/{post_id}", response_model=schemas.PostResponse)
def patch_post(
    post_id: int,
    post_in: schemas.PostPatch,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found."
        )
        
    update_data = post_in.dict(exclude_unset=True)
    
    # Check title uniqueness if title is being updated
    if "title" in update_data:
        check_duplicate_title(db, update_data["title"], exclude_id=post_id)
        
    for key, value in update_data.items():
        if key == "status" and value is not None:
            setattr(db_post, key, value.value)
        else:
            setattr(db_post, key, value)
            
    db.commit()
    db.refresh(db_post)
    return db_post


# 5. DELETE /posts/{post_id} - Delete a post
@app.delete("/posts/{post_id}", status_code=status.HTTP_200_OK)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found."
        )
        
    db.delete(db_post)
    db.commit()
    return {"message": "Post deleted successfully"}


# 6. POST /posts/{post_id}/view - Track views (increment by 1)
@app.post("/posts/{post_id}/view", response_model=schemas.PostViewResponse)
def increment_view(post_id: int, db: Session = Depends(get_db)):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found."
        )
        
    db_post.views += 1
    db.commit()
    db.refresh(db_post)
    
    return {"post_id": db_post.id, "views": db_post.views}


# 7. GET /dashboard/stats - Dashboard analytics
@app.get("/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_posts = db.query(models.Post).count()
    published_posts = db.query(models.Post).filter(models.Post.status == "published").count()
    draft_posts = db.query(models.Post).filter(models.Post.status == "draft").count()
    archived_posts = db.query(models.Post).filter(models.Post.status == "archived").count()
    
    total_views = db.query(func.sum(models.Post.views)).scalar() or 0
    
    # Get most viewed post (highest view count). Returns None if zero posts.
    most_viewed_post = db.query(models.Post).order_by(models.Post.views.desc()).first()
    
    return {
        "total_posts": total_posts,
        "published_posts": published_posts,
        "draft_posts": draft_posts,
        "archived_posts": archived_posts,
        "total_views": total_views,
        "most_viewed_post": most_viewed_post
    }


# AI Summary Generation: POST /posts/{post_id}/summarize
@app.post("/posts/{post_id}/summarize", response_model=schemas.PostResponse)
async def summarize_post(post_id: int, db: Session = Depends(get_db)):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found."
        )
        
    # Generate summary (falls back to truncation if Groq API fails)
    summary = await ai_service.generate_ai_summary(db_post.content)
    
    db_post.ai_summary = summary
    db_post.updated_at = func.now() # trigger updated_at time update
    db.commit()
    db.refresh(db_post)
    from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tghotnews.com",
        "https://www.tghotnews.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your routes below...
    
    return db_post
