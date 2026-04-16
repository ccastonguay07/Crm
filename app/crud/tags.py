from sqlalchemy.orm import Session

from app.models.tag import Tag


def get_tags(db: Session) -> list[Tag]:
    return db.query(Tag).order_by(Tag.name).all()


def create_tag(db: Session, name: str, color: str = "#6366f1") -> Tag:
    tag = Tag(name=name.strip().lower(), color=color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int) -> bool:
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        return False
    db.delete(tag)
    db.commit()
    return True
