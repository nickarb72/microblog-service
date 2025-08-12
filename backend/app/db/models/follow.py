from typing import Any, Dict

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class Follow(Base):
    __tablename__ = "follows"

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Кто подписан
    following_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # На кого подписан

    follower = relationship(
        "User",
        foreign_keys=[follower_id],
        back_populates="following",
    )
    following = relationship(
        "User",
        foreign_keys=[following_id],
        back_populates="followers",
    )

    def to_json(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}