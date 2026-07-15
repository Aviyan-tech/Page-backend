from enum import Enum
from datetime import datetime
from typing import Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

class PostStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class PostBase(BaseModel):
    title: str = Field(..., min_length=1, description="The title of the news post")
    content: str = Field(..., min_length=1, description="The content/body of the news post")
    category: str = Field(..., min_length=1, description="The category of the news post")
    status: PostStatus = Field(default=PostStatus.DRAFT, description="The status of the news post")

class PostCreate(PostBase):
    pass

class PostUpdate(PostBase):
    pass

class PostPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="The title of the news post")
    content: Optional[str] = Field(None, min_length=1, description="The content/body of the news post")
    category: Optional[str] = Field(None, min_length=1, description="The category of the news post")
    status: Optional[PostStatus] = Field(None, description="The status of the news post")


class PostResponse(PostBase):
    id: int
    views: int
    created_at: datetime
    ai_summary: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True

class PostViewResponse(BaseModel):
    post_id: int
    views: int

class MostViewedPostInfo(BaseModel):
    id: int
    title: str
    views: int

    class Config:
        orm_mode = True
        from_attributes = True

class DashboardStats(BaseModel):
    total_posts: int
    published_posts: int
    draft_posts: int
    archived_posts: int
    total_views: int
    most_viewed_post: Optional[MostViewedPostInfo] = None
