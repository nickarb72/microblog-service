from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from backend.app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False, index=True)

    tweets = relationship("Tweet", back_populates="author")
    likes = relationship("Like", back_populates="user")
    followers = relationship(
        "Follow",
        foreign_keys="Follow.following_id",
        back_populates="following",
    )
    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
    )
