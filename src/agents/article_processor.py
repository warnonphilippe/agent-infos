"""Article processing, filtering, and ranking utilities."""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class Article(BaseModel):
    """Article model with flexible field mapping."""
    
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    published_at: Optional[datetime] = Field(None, description="Publication date")
    content: str = Field(default="", description="Article content or summary")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    source: str = Field(default="", description="Source MCP server")
    
    @field_validator("published_at", mode="before")
    @classmethod
    def parse_published_at(cls, v: any) -> Optional[datetime]:
        """Parse published_at from various formats."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        try:
            return date_parser.parse(str(v))
        except (ValueError, TypeError):
            return None
    
    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: any) -> List[str]:
        """Normalize tags to a list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            # Handle comma-separated or space-separated tags
            return [tag.strip() for tag in v.replace(",", " ").split() if tag.strip()]
        if isinstance(v, list):
            return [str(tag).strip() for tag in v if tag]
        return []
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


def filter_articles_by_tags(
    articles: List[Dict],
    target_tags: List[str]
) -> List[Article]:
    """
    Filter articles that contain at least one of the target tags.
    
    Args:
        articles: List of article dictionaries
        target_tags: List of tags to filter by
        
    Returns:
        List of filtered Article objects
    """
    if not target_tags:
        return [Article(**article) for article in articles]
    
    # Normalize tags to lowercase for comparison
    target_tags_lower = [tag.lower().strip() for tag in target_tags if tag.strip()]
    
    filtered = []
    for article_dict in articles:
        try:
            article = Article(**article_dict)
            
            # Check if article has any matching tags
            article_tags_lower = [tag.lower() for tag in article.tags]
            has_matching_tag = any(
                target_tag in article_tags_lower or target_tag in article.title.lower()
                for target_tag in target_tags_lower
            )
            
            # Also check if any target tag appears in title or content
            if not has_matching_tag:
                title_lower = article.title.lower()
                content_lower = article.content.lower()
                has_matching_tag = any(
                    target_tag in title_lower or target_tag in content_lower
                    for target_tag in target_tags_lower
                )
            
            if has_matching_tag:
                filtered.append(article)
        except Exception as e:
            logger.warning(f"Error processing article {article_dict.get('title', 'unknown')}: {e}")
            continue
    
    return filtered


def rank_articles(articles: List[Article]) -> List[Article]:
    """
    Rank articles by relevance.
    
    Ranking criteria:
    1. Recency (more recent articles ranked higher)
    2. Number of matching tags
    3. Content length (longer articles may be more informative)
    
    Args:
        articles: List of Article objects to rank
        
    Returns:
        Ranked list of articles
    """
    now = datetime.utcnow()
    
    def calculate_score(article: Article) -> float:
        """Calculate relevance score for an article."""
        score = 0.0
        
        # Recency score (more recent = higher score)
        if article.published_at:
            days_old = (now - article.published_at).total_seconds() / 86400
            # Score decreases with age, but not too aggressively
            recency_score = max(0, 100 - days_old * 10)
            score += recency_score
        else:
            # Articles without date get a lower score
            score += 20
        
        # Tag count score (more tags = potentially more relevant)
        tag_score = min(len(article.tags) * 5, 30)
        score += tag_score
        
        # Content length score (longer content may be more informative)
        content_length = len(article.content)
        if content_length > 0:
            length_score = min(content_length / 100, 20)
            score += length_score
        
        return score
    
    # Sort by score (descending)
    ranked = sorted(articles, key=calculate_score, reverse=True)
    return ranked


def select_top_articles(articles: List[Article], top_n: int = 10) -> List[Article]:
    """
    Select the top N articles from a ranked list.
    
    Args:
        articles: List of ranked Article objects
        top_n: Number of top articles to select
        
    Returns:
        Top N articles
    """
    return articles[:top_n]


def load_tags_from_file(file_path: str) -> List[str]:
    """
    Load tags from a text file (one tag per line).
    
    Args:
        file_path: Path to the tags file
        
    Returns:
        List of tags
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tags = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        return tags
    except FileNotFoundError:
        logger.error(f"Tags file not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading tags file {file_path}: {e}")
        return []
