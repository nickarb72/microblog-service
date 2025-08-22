from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.app.db.session import Base
from backend.app.config import MAX_TEXT_SIZE


class Tweet(Base):
    __tablename__ = "tweets"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(MAX_TEXT_SIZE), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    author = relationship("User", back_populates="tweets")
    media = relationship(
        "TweetMedia", back_populates="tweet", cascade="all, delete-orphan"
    )
    likes = relationship("Like", back_populates="tweet", cascade="all, delete-orphan")


class TweetMedia(Base):
    __tablename__ = "tweet_media"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    tweet_id = Column(
        Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    tweet = relationship("Tweet", back_populates="media")
    user = relationship("User")


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tweet_id = Column(
        Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=False
    )

    user = relationship("User", back_populates="likes")
    tweet = relationship("Tweet", back_populates="likes")
