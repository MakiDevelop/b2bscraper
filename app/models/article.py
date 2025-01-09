from sqlalchemy import Column, Integer, String, Text, DateTime, Table, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base

# 關聯表
article_tags = Table(
    'article_tags',
    Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(500), unique=True, nullable=False)
    category = Column(String(100))
    summary = Column(Text)
    content = Column(Text)
    source = Column(String(50))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    tags = relationship('Tag', secondary=article_tags, back_populates='articles')

    def __repr__(self):
        return f"<Article {self.title}>"

class Tag(Base):
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    articles = relationship('Article', secondary=article_tags, back_populates='tags')
    
    def __repr__(self):
        return f"<Tag {self.name}>" 